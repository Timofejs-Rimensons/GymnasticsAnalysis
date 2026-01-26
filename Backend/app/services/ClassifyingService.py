import torch
import torch.nn as nn
import numpy as np
import os

class ClassifyingService:
    def __init__(self, model_cfg=None, num_classes=None, window_size=30, device='cpu', verbose=True):
        self.model_cfg = model_cfg
        self.num_classes = num_classes
        self.window_size = window_size
        self.device = torch.device(device)
        self.verbose = verbose
        self.model = None
        self.is_standalone = False

        # Only init architecture if config is provided (Training/Conversion mode)
        if self.model_cfg is not None and self.num_classes is not None:
            self._init_model()

    def _log(self, message):
        if self.verbose: print(f"[ClassifyingService] {message}")

    def _init_model(self):
        """Initializes architecture. Requires pyskl."""
        try:
            from pyskl.models import build_model
            self._log("Initializing architecture via pyskl...")
            self.model = build_model(self.model_cfg).to(self.device)

            # Ensure the classification head matches our classes
            if hasattr(self.model, 'cls_head') and hasattr(self.model.cls_head, 'fc_cls'):
                in_dims = self.model.cls_head.fc_cls.in_features
                self.model.cls_head.fc_cls = nn.Linear(in_dims, self.num_classes).to(self.device)
            self.is_standalone = False
        except ImportError:
            self._log("Notice: pyskl not found. Only standalone (.pt) models can be loaded.")

    def load_model(self, path):
        """Loads either .pt (Standalone) or .pth (Checkpoint) files."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")

        if path.endswith('.pt'):
            self._log("Loading standalone TorchScript model...")
            self.model = torch.jit.load(path, map_location=self.device)
            self.is_standalone = True
        else:
            self._log("Loading standard checkpoint (Requires pyskl)...")
            checkpoint = torch.load(path, map_location=self.device)
            self.model_cfg = checkpoint['cfg']
            self.num_classes = checkpoint['num_classes']
            self.window_size = checkpoint.get('window_size', 30)
            self._init_model() # Requires pyskl
            if self.model is None:
                raise ImportError("Cannot load .pth checkpoint without pyskl installed.")
            self.model.load_state_dict(checkpoint['state_dict'])
            self.is_standalone = False

        self.model.eval()
        self._log("Model loaded successfully.")

    def save_model(self, path, as_standalone=False):
        """Saves model. Use as_standalone=True for production export."""
        if self.model is None:
            raise ValueError("No model to save.")

        if as_standalone:
            self._log(f"Exporting standalone model to {path}...")
            self.model.eval()

            # 1. Create a dummy input: (Batch, Person, Time, Joint, Channel)
            dummy_input = torch.randn(1, 1, self.window_size, 17, 3).to(self.device)

            # 2. Define a wrapper to bypass the 'Label should not be None' error.
            # We trace THIS instead of the raw pyskl model.
            class TraceWrapper(torch.nn.Module):
                def __init__(self, model):
                    super().__init__()
                    self.model = model

                def forward(self, x):
                    # We bypass the model's main forward() and go straight
                    # to the inference path: extract features -> classify.
                    feat = self.model.extract_feat(x)
                    return self.model.cls_head(feat)

            wrapper = TraceWrapper(self.model)

            # 3. Trace the wrapper
            with torch.no_grad():
                traced_model = torch.jit.trace(wrapper, dummy_input)
                traced_model.save(path)

            self._log("Export complete.")
        else:
            self._log(f"Saving checkpoint to {path}...")
            checkpoint = {
                'state_dict': self.model.state_dict(),
                'cfg': self.model_cfg,
                'num_classes': self.num_classes,
                'window_size': self.window_size
            }
            torch.save(checkpoint, path)

    def _forward(self, bx):
        """Handles the different call signatures of raw vs standalone models."""
        if self.is_standalone:
            return self.model(bx)
        # Raw pyskl models often require manual head mapping
        feat = self.model.extract_feat(bx)
        return self.model.cls_head(feat)

    def predict_video(self, video_features, class_names=None, batch_size=64):
        """Sliding window prediction for a full video."""
        if self.model is None:
            raise ValueError("Model not loaded.")

        feat = np.array(video_features, dtype=np.float32)
        # Ensure shape is (T, V, C)
        if feat.ndim == 4: feat = feat[0]

        total_frames = feat.shape[0]
        half_window = self.window_size // 2
        padded_feat = np.pad(feat, [(half_window, half_window), (0, 0), (0, 0)], mode='edge')

        windows = []
        for i in range(total_frames):
            window = padded_feat[i:i + self.window_size]
            windows.append(window[np.newaxis, ...]) # Add Person dim: (1, T, V, C)

        windows = np.stack(windows, axis=0)
        all_preds = []

        with torch.no_grad():
            for i in range(0, len(windows), batch_size):
                batch = torch.as_tensor(windows[i:i + batch_size], device=self.device)
                logits = self._forward(batch)
                all_preds.extend(logits.argmax(1).cpu().numpy())

        return [class_names[p] for p in all_preds] if class_names else all_preds

    def _validate_sequence_shape(self, seq, seq_idx=0):
        """Validate and fix sequence shape to (M, T, V, C)."""
        seq = np.array(seq, dtype=np.float32)
        original_shape = seq.shape

        if seq.ndim == 3:
            seq = seq[np.newaxis, ...]

        if seq.ndim != 4:
            raise ValueError(f"Sequence {seq_idx}: Expected 3D or 4D array, got shape {original_shape}")

        M, T, V, C = seq.shape

        # Auto-transpose if V (joints) is 17 but in wrong dimension
        if V != 17:
            if C == 17:
                seq = seq.transpose(0, 1, 3, 2)
            elif M == 17:
                pass # Logic to handle other weird shapes could go here

        # Auto-transpose if C (channels) is 3 but in wrong dimension
        M, T, V, C = seq.shape
        if C != 3:
            if seq.shape[1] == 3: # (M, C, T, V) -> (M, T, V, C)
                seq = seq.transpose(0, 2, 3, 1)

        M, T, V, C = seq.shape
        if V != 17 or C != 3:
            raise ValueError(
                f"Sequence {seq_idx}: Shape validation failed. "
                f"Expected (M, T, 17, 3), got (M={M}, T={T}, V={V}, C={C})"
            )

        return seq

    def _prepare_training_data(self, x, y, padding='edge'):
        """Prepare training windows from sequences."""
        all_windows = []
        all_labels = []
        pad_size = self.window_size // 2

        skipped = 0

        for seq_idx, (seq_x, seq_y) in enumerate(zip(x, y)):
            if seq_x is None or len(seq_x) == 0:
                skipped += 1
                continue

            try:
                seq_x = self._validate_sequence_shape(seq_x, seq_idx)
                seq_y = np.array(seq_y)
            except ValueError as e:
                self._log(f"  [Warning] {e}")
                skipped += 1
                continue

            T = seq_x.shape[1]

            if T < self.window_size:
                skipped += 1
                continue

            if padding is not None:
                pad_width_x = [(0, 0), (pad_size, pad_size), (0, 0), (0, 0)]
                seq_x = np.pad(seq_x, pad_width_x, mode='edge')

                if seq_y.ndim == 1:
                    seq_y = np.pad(seq_y, (pad_size, pad_size), mode='edge')
                else:
                    pad_width_y = [(pad_size, pad_size)] + [(0, 0)] * (seq_y.ndim - 1)
                    seq_y = np.pad(seq_y, pad_width_y, mode='edge')

            T_padded = seq_x.shape[1]

            for i in range(T_padded - self.window_size + 1):
                window = seq_x[:, i:i + self.window_size, :, :]
                label = seq_y[i + pad_size]
                all_windows.append(window)
                all_labels.append(label)

        if not all_windows:
            raise ValueError("No valid windows created! Check your input data shapes.")

        return np.stack(all_windows, axis=0), np.array(all_labels)

    def _augment_batch(self, bx, aug_range):
        if aug_range is None:
            return bx
        low, high = aug_range
        N, M, T, V, C = bx.shape
        scales = torch.empty(N, 1, 1, V, C, device=bx.device, dtype=bx.dtype).uniform_(low, high)
        return bx * scales

    def fit(self, x_train, y_train, x_val=None, y_val=None, epochs=50, lr=1e-3, batch_size=32, aug_range=None):
        if self.model is None:
            raise ValueError("Model not initialized. Provide model_cfg and num_classes.")

        self._log(f"Starting Training: {epochs} epochs, lr={lr}, batch={batch_size}")

        if hasattr(self.model, 'backbone'):
            for param in self.model.backbone.parameters():
                param.requires_grad = False

        trainable_params = [p for p in self.model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(trainable_params, lr=lr)
        criterion = nn.CrossEntropyLoss()

        train_windows, train_labels = self._prepare_training_data(x_train, y_train)

        if train_labels.ndim > 1 and train_labels.shape[1] > 1:
            train_targets = np.argmax(train_labels, axis=1)
        else:
            train_targets = train_labels.astype(np.int64)

        has_val = x_val is not None and y_val is not None
        if has_val:
            val_windows, val_labels = self._prepare_training_data(x_val, y_val)
            val_targets = np.argmax(val_labels, axis=1) if val_labels.ndim > 1 else val_labels.astype(np.int64)

        for epoch in range(epochs):
            self.model.train()
            indices = np.random.permutation(len(train_windows))
            total_loss = 0.0
            correct = 0

            for batch_idx in range(0, len(indices), batch_size):
                batch_indices = indices[batch_idx:batch_idx + batch_size]

                bx = torch.as_tensor(train_windows[batch_indices], dtype=torch.float32, device=self.device)
                by = torch.as_tensor(train_targets[batch_indices], dtype=torch.long, device=self.device)

                bx = self._augment_batch(bx, aug_range)

                optimizer.zero_grad()
                logits = self._forward(bx)
                loss = criterion(logits, by)
                loss.backward()
                optimizer.step()

                total_loss += loss.item() * len(batch_indices)
                correct += (logits.argmax(1) == by).sum().item()

            train_loss = total_loss / len(train_windows)
            train_acc = correct / len(train_windows)

            val_str = ""
            if has_val:
                val_loss, val_acc = self._evaluate(val_windows, val_targets, criterion, batch_size)
                val_str = f" | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2%}"
                self.history['val_loss'].append(val_loss)
                self.history['val_acc'].append(val_acc)

            self.history['loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)

            self._log(f"Epoch {epoch+1:3d}/{epochs} | Loss: {train_loss:.4f} | Acc: {train_acc:.2%}{val_str}")

    def _evaluate(self, windows, targets, criterion, batch_size):
        self.model.eval()
        total_loss = 0.0
        correct = 0
        with torch.no_grad():
            for i in range(0, len(windows), batch_size):
                batch_indices = np.arange(i, min(i + batch_size, len(windows)))
                bx = torch.as_tensor(windows[batch_indices], dtype=torch.float32, device=self.device)
                by = torch.as_tensor(targets[batch_indices], dtype=torch.long, device=self.device)
                logits = self._forward(bx)
                total_loss += criterion(logits, by).item() * len(batch_indices)
                correct += (logits.argmax(1) == by).sum().item()
        return total_loss / len(windows), correct / len(windows)

    def _load_temp_model(self, model_path):
        """Helper to load a temporary model instance from path."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        checkpoint = torch.load(model_path, map_location=self.device)

        # We only import pyskl here, so normal usage without model loading doesn't crash
        try:
            from pyskl.models import build_model
        except ImportError:
            raise ImportError("pyskl is required to load the model architecture.")

        cfg = checkpoint['cfg']
        num_classes = checkpoint['num_classes']

        model = build_model(cfg).to(self.device)

        if hasattr(model, 'cls_head') and hasattr(model.cls_head, 'fc_cls'):
            head = model.cls_head.fc_cls
            in_dims = head.in_features
            model.cls_head.fc_cls = nn.Linear(in_dims, num_classes).to(self.device)

        model.load_state_dict(checkpoint['state_dict'])
        model.eval()
        return model, checkpoint.get('window_size', 30)

    def predict(self, x, model_path=None, return_probas=False):
        """
        Predict classes for input sequences.

        Args:
            x: Input sequences
            model_path: Optional path to load a model specifically for this prediction.
                        If provided, loads model, predicts, then deletes model.
        """
        temp_model = None
        active_model = self.model

        if model_path:
            self._log(f"Loading temporary model from {model_path} for prediction...")
            temp_model, _ = self._load_temp_model(model_path)
            active_model = temp_model

        if active_model is None:
            raise ValueError("No model initialized and no model_path provided.")

        active_model.eval()
        x = np.array(x, dtype=np.float32)

        if x.ndim == 3:
            x = x[np.newaxis, np.newaxis, ...]
        elif x.ndim == 4:
            x = x[np.newaxis, ...]

        with torch.no_grad():
            bx = torch.as_tensor(x, dtype=torch.float32, device=self.device)
            logits = self._forward(bx, model=active_model)
            probas = torch.softmax(logits, dim=1)

            result = probas.cpu().numpy() if return_probas else probas.argmax(1).cpu().numpy()

        # Cleanup temp model
        if temp_model:
            del temp_model
            torch.cuda.empty_cache()

        return result
