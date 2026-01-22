import torch
import torch.nn as nn
import numpy as np
import time


class ClassifyingService:
    """
    Skeleton-based action classifier using STGCN backbone.
    
    Expected input format per sequence: (M, T, V, C)
        - M: number of persons (typically 1)
        - T: number of frames
        - V: number of joints (17 for COCO)
        - C: channels (3 for x, y, confidence)
    
    Model (RecognizerGCN) expects: (N, M, T, V, C)
        - N: batch size
    """
    
    def __init__(self, model_cfg=None, num_classes=None, window_size=30, device='cpu', verbose=True, **kwargs):
        self.model_cfg = model_cfg
        self.num_classes = num_classes
        self.window_size = window_size
        self.device = torch.device(device)
        self.verbose = verbose
        self.history = {'loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
        self.model = None
        
        if self.model_cfg is not None and self.num_classes is not None:
            self._init_model()

    def _log(self, message):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _init_model(self):
        """Initialize the STGCN model."""
        from pyskl.models import build_model
        
        self._log("=" * 60)
        self._log("Initializing Model...")
        self._log(f"  - Device: {self.device}")
        self._log(f"  - Num Classes: {self.num_classes}")
        self._log(f"  - Window Size: {self.window_size}")
        
        self.model = build_model(self.model_cfg).to(self.device)
        
        if hasattr(self.model, 'backbone'):
            backbone = self.model.backbone
            if hasattr(backbone, 'data_bn'):
                bn_features = backbone.data_bn.num_features
                self._log(f"  - Backbone data_bn: BatchNorm1d({bn_features})")
        
        if hasattr(self.model, 'cls_head') and hasattr(self.model.cls_head, 'fc_cls'):
            head = self.model.cls_head.fc_cls
            in_dims = head.in_features
            self.model.cls_head.fc_cls = nn.Linear(in_dims, self.num_classes).to(self.device)
            self._log(f"  - Classification head: Linear({in_dims}, {self.num_classes})")
        
        total_params = sum(p.numel() for p in self.model.parameters())
        self._log(f"  - Total parameters: {total_params:,}")
        
        self._log("Model initialized successfully!")
        self._log("=" * 60)

    def _validate_sequence_shape(self, seq, seq_idx=0):
        """Validate and fix sequence shape to (M, T, V, C)."""
        seq = np.array(seq, dtype=np.float32)
        original_shape = seq.shape
        
        if seq.ndim == 3:
            seq = seq[np.newaxis, ...]
            if seq_idx == 0:
                self._log(f"  [Shape Fix] {original_shape} -> {seq.shape} (added M dimension)")
        
        if seq.ndim != 4:
            raise ValueError(f"Sequence {seq_idx}: Expected 3D or 4D array, got shape {original_shape}")
        
        M, T, V, C = seq.shape
        
        if V != 17:
            if C == 17:
                seq = seq.transpose(0, 1, 3, 2)
                M, T, V, C = seq.shape
                if seq_idx == 0:
                    self._log(f"  [Shape Fix] Transposed last two axes: {original_shape} -> {seq.shape}")
            elif M == 17:
                raise ValueError(
                    f"Sequence {seq_idx}: Unusual shape {original_shape}. "
                    f"Expected (M, T, V, C) where V=17 joints, C=3 coords."
                )
        
        if C != 3:
            if seq.shape[1] == 3:
                seq = seq.transpose(0, 2, 3, 1)
                M, T, V, C = seq.shape
                if seq_idx == 0:
                    self._log(f"  [Shape Fix] Detected (M,C,T,V), transposed: {original_shape} -> {seq.shape}")
        
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
        
        self._log("\n" + "=" * 60)
        self._log("Preparing Training Data...")
        self._log(f"  - Number of sequences: {len(x)}")
        self._log(f"  - Window size: {self.window_size}")
        self._log(f"  - Padding: {padding} (pad_size={pad_size})")
        
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
            
            M, T, V, C = seq_x.shape
            
            if seq_idx == 0:
                self._log(f"\n  First sequence analysis:")
                self._log(f"    - Shape (M, T, V, C): {seq_x.shape}")
                self._log(f"    - Labels shape: {seq_y.shape}")
                self._log(f"    - Data range: [{seq_x.min():.3f}, {seq_x.max():.3f}]")
            
            if T < self.window_size:
                self._log(f"  [Warning] Seq {seq_idx}: T={T} < window_size={self.window_size}, skipping")
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
        
        windows_array = np.stack(all_windows, axis=0)
        labels_array = np.array(all_labels)
        
        self._log(f"\n  Data preparation complete:")
        self._log(f"    - Sequences processed: {len(x) - skipped}/{len(x)}")
        self._log(f"    - Total windows: {len(windows_array)}")
        self._log(f"    - Windows shape: {windows_array.shape}")
        self._log(f"    - Expected: (N, M=1, T={self.window_size}, V=17, C=3)")
        self._log(f"    - Labels shape: {labels_array.shape}")
        
        N, M, T, V, C = windows_array.shape
        assert M == 1, f"Expected M=1, got M={M}"
        assert T == self.window_size, f"Expected T={self.window_size}, got T={T}"
        assert V == 17, f"Expected V=17, got V={V}"
        assert C == 3, f"Expected C=3, got C={C}"
        
        self._log("    ✓ Shape validation passed!")
        self._log("=" * 60 + "\n")
        
        return windows_array, labels_array

    def _augment_batch(self, bx, aug_range):
        """
        Apply augmentation: multiply each value by a unique random scale per sample/joint/channel.
        
        Args:
            bx: Tensor of shape (N, M, T, V, C)
            aug_range: Tuple (min_scale, max_scale), e.g., (0.9, 1.1)
        
        Returns:
            Augmented tensor of same shape
        
        Each joint and each channel gets its own random multiplier (consistent across time).
        Shape of random multipliers: (N, 1, 1, V, C)
        """
        if aug_range is None:
            return bx
        
        low, high = aug_range
        N, M, T, V, C = bx.shape
        
        # Generate unique random scale for each sample, joint, and channel
        # Shape: (N, 1, 1, V, C) - same scale across M (persons) and T (time)
        scales = torch.empty(N, 1, 1, V, C, device=bx.device, dtype=bx.dtype).uniform_(low, high)
        
        return bx * scales

    def _forward(self, bx):
        """Forward pass using model's extract_feat method."""
        feat = self.model.extract_feat(bx)
        logits = self.model.cls_head(feat)
        return logits

    def fit(self, x_train, y_train, x_val=None, y_val=None, epochs=50, lr=1e-3, batch_size=32, aug_range=None):
        """
        Train the classifier.
        
        Args:
            x_train: List of training sequences, each (M, T, V, C) or (T, V, C)
            y_train: List of training labels
            x_val: Optional validation sequences
            y_val: Optional validation labels
            epochs: Number of training epochs
            lr: Learning rate
            batch_size: Batch size
            aug_range: Tuple (min_scale, max_scale) for augmentation, e.g., (0.9, 1.1)
                       Each joint's each channel value is multiplied by a unique random
                       value from this range. Set to None to disable augmentation.
        """
        if self.model is None:
            raise ValueError("Model not initialized. Provide model_cfg and num_classes.")

        self._log("\n" + "=" * 60)
        self._log("Starting Training...")
        self._log("=" * 60)

        # Freeze backbone, train only head
        if hasattr(self.model, 'backbone'):
            for param in self.model.backbone.parameters():
                param.requires_grad = False
            self._log("Backbone frozen. Training classification head only.")
        
        trainable_params = [p for p in self.model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(trainable_params, lr=lr)
        criterion = nn.CrossEntropyLoss()
        
        self._log(f"Optimizer: AdamW (lr={lr})")
        self._log(f"Trainable parameters: {sum(p.numel() for p in trainable_params):,}")
        
        # Log augmentation
        if aug_range is not None:
            self._log(f"Augmentation: scale range ({aug_range[0]}, {aug_range[1]})")
        else:
            self._log("Augmentation: disabled")
        
        # Prepare data
        train_windows, train_labels = self._prepare_training_data(x_train, y_train)
        
        if train_labels.ndim > 1 and train_labels.shape[1] > 1:
            train_targets = np.argmax(train_labels, axis=1)
        else:
            train_targets = train_labels.astype(np.int64)
        
        has_val = x_val is not None and y_val is not None
        if has_val:
            val_windows, val_labels = self._prepare_training_data(x_val, y_val)
            if val_labels.ndim > 1 and val_labels.shape[1] > 1:
                val_targets = np.argmax(val_labels, axis=1)
            else:
                val_targets = val_labels.astype(np.int64)

        # Debug info
        self._log("\n" + "-" * 40)
        self._log("Debug: Input shape verification")
        self._log("-" * 40)
        self._log(f"  Train windows shape (N, M, T, V, C): {train_windows.shape}")
        self._log(f"  Model expects: (N, M, T, V, C) -> extract_feat handles permutation")
        self._log("-" * 40 + "\n")

        # Training loop
        for epoch in range(epochs):
            epoch_start = time.time()
            self.model.train()
            
            indices = np.random.permutation(len(train_windows))
            total_loss = 0.0
            correct = 0
            
            for batch_idx in range(0, len(indices), batch_size):
                batch_indices = indices[batch_idx:batch_idx + batch_size]
                
                bx = torch.as_tensor(
                    train_windows[batch_indices], 
                    dtype=torch.float32, 
                    device=self.device
                )
                by = torch.as_tensor(
                    train_targets[batch_indices], 
                    dtype=torch.long, 
                    device=self.device
                )
                
                # Apply augmentation during training
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
            
            val_loss, val_acc = 0.0, 0.0
            if has_val:
                val_loss, val_acc = self._evaluate(val_windows, val_targets, criterion, batch_size)
            
            self.history['loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)
            
            elapsed = time.time() - epoch_start
            eta = (epochs - epoch - 1) * elapsed
            
            self._log(
                f"Epoch {epoch+1:3d}/{epochs} | "
                f"Loss: {train_loss:.4f} | Acc: {train_acc:.2%} | "
                f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2%} | "
                f"{elapsed:.1f}s | ETA: {eta/60:.1f}min"
            )
        
        self._log("\n" + "=" * 60)
        self._log("Training Complete!")
        self._log(f"  Final Train Acc: {train_acc:.2%}")
        if has_val:
            self._log(f"  Final Val Acc: {val_acc:.2%}")
        self._log("=" * 60 + "\n")

    def _evaluate(self, windows, targets, criterion, batch_size):
        """Evaluate model on given data (no augmentation)."""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        
        with torch.no_grad():
            for i in range(0, len(windows), batch_size):
                batch_indices = np.arange(i, min(i + batch_size, len(windows)))
                
                bx = torch.as_tensor(
                    windows[batch_indices], 
                    dtype=torch.float32, 
                    device=self.device
                )
                by = torch.as_tensor(
                    targets[batch_indices], 
                    dtype=torch.long, 
                    device=self.device
                )
                
                logits = self._forward(bx)
                total_loss += criterion(logits, by).item() * len(batch_indices)
                correct += (logits.argmax(1) == by).sum().item()
        
        return total_loss / len(windows), correct / len(windows)

    def predict(self, x, return_probas=False):
        """Predict classes for input sequences."""
        if self.model is None:
            raise ValueError("Model not initialized.")
        
        self.model.eval()
        x = np.array(x, dtype=np.float32)
        
        if x.ndim == 3:
            x = x[np.newaxis, np.newaxis, ...]
        elif x.ndim == 4:
            x = x[np.newaxis, ...]
        
        with torch.no_grad():
            bx = torch.as_tensor(x, dtype=torch.float32, device=self.device)
            logits = self._forward(bx)
            probas = torch.softmax(logits, dim=1)
            
            if return_probas:
                return probas.cpu().numpy()
            return probas.argmax(1).cpu().numpy()

    def predict_frame_by_frame(self, video_features, class_names=None, batch_size=64):
        """Predict class for each frame using sliding window."""
        if self.model is None:
            raise ValueError("Model not initialized.")

        feat = np.array(video_features, dtype=np.float32)
        if feat.ndim == 4 and feat.shape[0] == 1:
            feat = feat[0]
        elif feat.ndim == 4:
            feat = feat[0]
        
        total_frames = feat.shape[0]
        half_window = self.window_size // 2

        padded_feat = np.pad(
            feat, 
            [(half_window, half_window), (0, 0), (0, 0)], 
            mode='edge'
        )

        all_windows = []
        for i in range(total_frames):
            window = padded_feat[i:i + self.window_size]
            window = window[np.newaxis, ...]
            all_windows.append(window)
        
        all_windows = np.stack(all_windows, axis=0)

        self.model.eval()
        all_preds = []
        
        with torch.no_grad():
            for i in range(0, len(all_windows), batch_size):
                batch = all_windows[i:i + batch_size]
                bx = torch.as_tensor(batch, dtype=torch.float32, device=self.device)
                logits = self._forward(bx)
                preds = logits.argmax(1).cpu().numpy()
                all_preds.extend(preds)

        if class_names:
            return [class_names[p] for p in all_preds]
        return all_preds

    def save_model(self, path):
        """Save model checkpoint."""
        checkpoint = {
            'state_dict': self.model.state_dict(),
            'cfg': self.model_cfg,
            'num_classes': self.num_classes,
            'window_size': self.window_size,
            'history': self.history
        }
        torch.save(checkpoint, path)
        self._log(f"Model saved to {path}")

    def load_model(self, path):
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.model_cfg = checkpoint['cfg']
        self.num_classes = checkpoint['num_classes']
        self.window_size = checkpoint.get('window_size', self.window_size)
        self.history = checkpoint.get('history', self.history)
        self._init_model()
        self.model.load_state_dict(checkpoint['state_dict'])
        self.model.eval()
        self._log(f"Model loaded from {path}")

    @classmethod
    def load(cls, path, device='cpu', verbose=True):
        """Class method to load a saved model."""
        instance = cls(model_cfg=None, num_classes=None, device=device, verbose=verbose)
        instance.load_model(path)
        return instance