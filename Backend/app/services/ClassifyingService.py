import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torch.nn.utils.rnn import pad_sequence
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
from tqdm import tqdm

from models.PoseGRUModel import PoseGRUModel

class ClassifyingService:
    """
    Per-frame classifier using sliding windows with PoseGRUModel.
    Each frame gets a prediction based on its surrounding context window.
    """
    
    def __init__(
        self,
        num_classes=None,
        input_size = None,
        window_size=30,
        stride=1,
        hidden_size=128,
        num_layers=2,
        dropout=0.3,
        learning_rate=1e-3,
        batch_size=32,
        epochs=100,
        patience=10,
        device=None,
        class_names=None,
        verbose=True,
        augment=True,
        augment_scale_range=(0.99, 1.01),
        model_path=None,
        use_joint_attention=True,
        use_temporal_attention=True,
        padding_mode='edge'
    ):
        self.num_classes = num_classes
        self.input_size = input_size
        self.window_size = window_size
        self.stride = stride
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.patience = patience
        self.verbose = verbose
        if num_classes:
            self.class_names = class_names or [f'Class_{i}' for i in range(num_classes)]
        else:
            self.class_names = class_names
        self.augment = augment
        self.augment_scale_range = augment_scale_range
        self.use_joint_attention = use_joint_attention
        self.use_temporal_attention = use_temporal_attention
        self.padding_mode = padding_mode
        
        self.device = torch.device(
            device if device else ('cuda:0' if torch.cuda.is_available() else 'cpu')
        )
        
        if model_path:
            self.model = torch.load(model_path, weights_only=False)
            self.model.eval()
        else:
            self.model = None
        
        self.history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}

    def set_model(self, model):
        """Sets the model for the service."""
        self.model = model.to(self.device)

    def set_hyperparameters(self, **kwargs):
        """Sets hyperparameters for the service."""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def _build_model(self, input_size):
        self.input_size = input_size
        if self.num_classes is None:
            raise ValueError("num_classes must be set before building the model.")
        self.model = PoseGRUModel(
            num_joint_features=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            num_classes=self.num_classes,
            dropout=self.dropout,
            use_joint_attention=self.use_joint_attention,
            use_temporal_attention=self.use_temporal_attention
        ).to(self.device)
    
    def _create_windows(self, features, targets=None):
        """
        Create sliding windows from a sequence.
        
        Args:
            features: (num_frames, num_features)
            targets: (num_frames, num_classes) or (num_frames,) or None
        
        Returns:
            windows: List of (window_size, num_features) arrays
            window_targets: List of target labels (for center frame or majority vote)
            frame_indices: List of frame indices that each window represents
        """
        num_frames = len(features)
        
        # Pad the sequence if necessary
        if num_frames < self.window_size:
            pad_amount = self.window_size - num_frames
            if self.padding_mode == 'edge':
                # Repeat edge values
                features = np.pad(features, ((0, pad_amount), (0, 0)), mode='edge')
                if targets is not None:
                    if targets.ndim == 2:
                        targets = np.pad(targets, ((0, pad_amount), (0, 0)), mode='edge')
                    else:
                        targets = np.pad(targets, (0, pad_amount), mode='edge')
            elif self.padding_mode == 'reflect':
                features = np.pad(features, ((0, pad_amount), (0, 0)), mode='reflect')
                if targets is not None:
                    if targets.ndim == 2:
                        targets = np.pad(targets, ((0, pad_amount), (0, 0)), mode='reflect')
                    else:
                        targets = np.pad(targets, (0, pad_amount), mode='reflect')
            else:  # zero padding
                features = np.pad(features, ((0, pad_amount), (0, 0)), mode='constant')
                if targets is not None:
                    if targets.ndim == 2:
                        # For one-hot, pad with zeros
                        targets = np.pad(targets, ((0, pad_amount), (0, 0)), mode='constant')
                    else:
                        # For class indices, pad with the most common class or 0
                        targets = np.pad(targets, (0, pad_amount), mode='constant')
            num_frames = len(features)
        
        windows = []
        window_targets = []
        frame_indices = []
        
        # Add padding for centered windows
        half_window = self.window_size // 2
        
        if self.padding_mode == 'edge':
            padded_features = np.pad(features, ((half_window, half_window), (0, 0)), mode='edge')
            if targets is not None:
                if targets.ndim == 2:
                    padded_targets = np.pad(targets, ((half_window, half_window), (0, 0)), mode='edge')
                else:
                    padded_targets = np.pad(targets, (half_window, half_window), mode='edge')
        elif self.padding_mode == 'reflect':
            padded_features = np.pad(features, ((half_window, half_window), (0, 0)), mode='reflect')
            if targets is not None:
                if targets.ndim == 2:
                    padded_targets = np.pad(targets, ((half_window, half_window), (0, 0)), mode='reflect')
                else:
                    padded_targets = np.pad(targets, (half_window, half_window), mode='reflect')
        else:
            padded_features = np.pad(features, ((half_window, half_window), (0, 0)), mode='constant')
            if targets is not None:
                if targets.ndim == 2:
                    padded_targets = np.pad(targets, ((half_window, half_window), (0, 0)), mode='constant')
                else:
                    padded_targets = np.pad(targets, (half_window, half_window), mode='constant')
        
        # Create windows
        for i in range(0, num_frames, self.stride):
            # Window centered at frame i
            start = i
            end = start + self.window_size
            
            window = padded_features[start:end]
            windows.append(window)
            
            # Target is the center frame's label
            if targets is not None:
                center_idx = start + half_window
                if padded_targets.ndim == 2:
                    # One-hot encoded
                    target = np.argmax(padded_targets[center_idx])
                else:
                    target = int(padded_targets[center_idx])
                window_targets.append(target)
            
            frame_indices.append(i)
        
        return windows, window_targets if targets is not None else None, frame_indices
    
    def _prepare_batch_windows(self, sequences, targets=None):
        """
        Create windows from multiple sequences and prepare them as a batch.
        """
        all_windows = []
        all_targets = []
        all_seq_ids = []
        all_frame_ids = []
        
        for seq_id, (seq_features, seq_targets) in enumerate(
            zip(sequences, targets) if targets is not None else zip(sequences, [None] * len(sequences))
        ):
            windows, window_targets, frame_indices = self._create_windows(seq_features, seq_targets)
            all_windows.extend(windows)
            if window_targets is not None:
                all_targets.extend(window_targets)
            all_seq_ids.extend([seq_id] * len(windows))
            all_frame_ids.extend(frame_indices)
        
        return all_windows, all_targets if all_targets else None, all_seq_ids, all_frame_ids
    
    def _augment_windows(self, windows):
        """Apply augmentation to windows."""
        if not self.augment:
            return windows
            
        augmented = []
        low, high = self.augment_scale_range
        
        for window in windows:
            scale = np.random.uniform(low, high, size=window.shape).astype(window.dtype)
            augmented.append(window * scale)
        
        return augmented
    
    def fit(self, x_train, y_train, x_val=None, y_val=None):
        """
        Train on sequences with per-frame labels using sliding windows.
        
        Args:
            x_train: List of sequences, each of shape (num_frames, num_features)
            y_train: List of frame-level labels, each of shape (num_frames, num_classes) or (num_frames,)
            x_val: Optional validation sequences
            y_val: Optional validation labels
        """
        
        # Build model
        input_size = x_train[0].shape[1]
        self._build_model(input_size)
        
        # Create all windows from training data
        if self.verbose:
            print(f"Creating windows with size {self.window_size} and stride {self.stride}...")
        
        train_windows, train_targets, train_seq_ids, train_frame_ids = self._prepare_batch_windows(x_train, y_train)
        n_windows = len(train_windows)
        
        if self.verbose:
            print(f"Created {n_windows} training windows from {len(x_train)} sequences")
        
        # Prepare validation windows if provided
        val_windows = None
        val_targets = None
        if x_val is not None:
            val_windows, val_targets, _, _ = self._prepare_batch_windows(x_val, y_val)
            if self.verbose:
                print(f"Created {len(val_windows)} validation windows from {len(x_val)} sequences")
        
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', patience=5, factor=0.5
        )
        
        best_val_loss = float('inf')
        best_model_state = None
        patience_counter = 0
        
        epoch_iterator = range(self.epochs)
        if self.verbose:
            epoch_iterator = tqdm(epoch_iterator, desc='Training')
        
        for epoch in epoch_iterator:
            self.model.train()
            
            # Shuffle windows
            indices = np.random.permutation(n_windows)
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            # Process in batches
            for batch_start in range(0, n_windows, self.batch_size):
                batch_end = min(batch_start + self.batch_size, n_windows)
                batch_indices = indices[batch_start:batch_end]
                
                # Get batch windows and targets
                batch_windows = [train_windows[i] for i in batch_indices]
                batch_targets = [train_targets[i] for i in batch_indices]
                
                # Augment if enabled
                if self.augment:
                    batch_windows = self._augment_windows(batch_windows)
                
                # Convert to tensors
                batch_x = torch.FloatTensor(np.array(batch_windows)).to(self.device)
                batch_y = torch.LongTensor(batch_targets).to(self.device)
                
                optimizer.zero_grad()
                
                # Forward pass - each window gets one prediction
                logits, _, _ = self.model(batch_x)
                
                # Compute loss
                loss = criterion(logits, batch_y)
                loss.backward()
                
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                
                # Calculate accuracy
                preds = logits.argmax(dim=-1)
                train_correct += (preds == batch_y).sum().item()
                train_total += len(batch_y)
                train_loss += loss.item() * len(batch_y)
            
            train_loss /= train_total
            train_acc = train_correct / train_total
            
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            
            # Validation
            val_loss, val_acc = 0, 0
            if val_windows is not None:
                val_loss, val_acc = self._evaluate_windows(val_windows, val_targets, criterion)
                self.history['val_loss'].append(val_loss)
                self.history['val_acc'].append(val_acc)
                
                scheduler.step(val_loss)
                
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    best_model_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                    patience_counter = 0
                else:
                    patience_counter += 1
                
                if patience_counter >= self.patience:
                    if self.verbose:
                        print(f'\nEarly stopping at epoch {epoch + 1}')
                    break
            
            if self.verbose:
                desc = f'Loss: {train_loss:.4f}, Acc: {train_acc:.4f}'
                if val_windows is not None:
                    desc += f' | Val: {val_loss:.4f}, {val_acc:.4f}'
                epoch_iterator.set_postfix_str(desc)
        
        # Load best model
        if best_model_state:
            self.model.load_state_dict(best_model_state)
        
        return self
    
    @torch.no_grad()
    def _evaluate_windows(self, windows, targets, criterion):
        """Evaluate on a set of windows."""
        self.model.eval()
        
        total_loss = 0
        total_correct = 0
        total_samples = 0
        
        for batch_start in range(0, len(windows), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(windows))
            
            batch_windows = windows[batch_start:batch_end]
            batch_targets = targets[batch_start:batch_end]
            
            batch_x = torch.FloatTensor(np.array(batch_windows)).to(self.device)
            batch_y = torch.LongTensor(batch_targets).to(self.device)
            
            logits, _, _ = self.model(batch_x)
            
            loss = criterion(logits, batch_y)
            total_loss += loss.item() * len(batch_y)
            
            preds = logits.argmax(dim=-1)
            total_correct += (preds == batch_y).sum().item()
            total_samples += len(batch_y)
        
        return total_loss / total_samples, total_correct / total_samples

    def _filter_short_poses(self, predictions, min_duration):
        """Merges pose segments that are shorter than min_duration."""
        if min_duration is None or min_duration <= 1:
            return predictions

        new_predictions = predictions.copy()
        num_frames = len(new_predictions)
        i = 0
        while i < num_frames:
            current_pose = new_predictions[i]
            j = i
            while j < num_frames and new_predictions[j] == current_pose:
                j += 1
            
            duration = j - i
            if duration < min_duration:
                # Merge with the previous pose if it's not the first segment
                if i > 0:
                    prev_pose = new_predictions[i - 1]
                    for k in range(i, j):
                        new_predictions[k] = prev_pose
            i = j
        return new_predictions

    @torch.no_grad()
    def predict_frames(self, x, return_probabilities=True, return_attention=False, smoothing_window=20, min_pose_duration=10, inertia_factor=0.5):
        """
        Predict per-frame labels for sequences using sliding windows.
        
        Args:
            x: List of sequences, each of shape (num_frames, num_features)
            return_probabilities: Whether to return class probabilities.
            return_attention: Whether to return attention weights.
            smoothing_window: Size of the window for probability smoothing.
            min_pose_duration: Minimum number of consecutive frames for a pose to be kept.
            inertia_factor: Factor to boost probabilities based on the previous frame's prediction.

        Returns:
            predictions: List of per-frame predictions for each sequence.
            probabilities: (optional) List of per-frame probability distributions.
            attention: (optional) Dict with temporal and joint attention for each window.
        """
        self._check_fitted()
        self.model.eval()
        
        all_predictions = []
        all_probabilities = []
        all_attention = {'temporal': [], 'joint': []} if return_attention else None
        
        for seq_features in x:
            num_frames = len(seq_features)
            
            # Create windows
            windows, _, frame_indices = self._create_windows(seq_features, None)
            
            if len(windows) == 0:
                # Handle empty sequence
                all_predictions.append(np.zeros(num_frames, dtype=np.int32))
                if return_probabilities:
                    all_probabilities.append(np.zeros((num_frames, self.num_classes)))
                continue
            
            # Predict in batches
            seq_predictions = np.zeros(num_frames, dtype=np.int32)
            seq_probabilities = np.zeros((num_frames, self.num_classes)) if return_probabilities else None
            
            for batch_start in range(0, len(windows), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(windows))
                batch_windows = windows[batch_start:batch_end]
                batch_frame_indices = frame_indices[batch_start:batch_end]
                
                # Convert to tensor
                batch_x = torch.FloatTensor(np.array(batch_windows)).to(self.device)
                
                # Forward pass
                logits, temporal_weights, joint_weights = self.model(batch_x)
                
                # Get predictions and probabilities
                preds = logits.argmax(dim=-1).cpu().numpy()
                if return_probabilities:
                    probs = torch.softmax(logits, dim=-1).cpu().numpy()
                
                # Assign predictions to corresponding frames
                for i, frame_idx in enumerate(batch_frame_indices):
                    if frame_idx < num_frames:
                        seq_predictions[frame_idx] = preds[i]
                        if return_probabilities:
                            seq_probabilities[frame_idx] = probs[i]
                
                # Store attention if requested
                if return_attention:
                    if temporal_weights is not None:
                        all_attention['temporal'].extend(temporal_weights.cpu().numpy())
                    if joint_weights is not None:
                        all_attention['joint'].extend(joint_weights.cpu().numpy())
            
            if return_probabilities: # Always apply inertia if probabilities are returned
                seq_probabilities = self._apply_temporal_inertia(
                    seq_probabilities, 
                    smoothing_window=smoothing_window,
                    inertia_factor=inertia_factor
                )
                seq_predictions = np.argmax(seq_probabilities, axis=1)

            # Post-process to remove short pose segments
            if min_pose_duration:
                seq_predictions = self._filter_short_poses(seq_predictions, min_pose_duration)

            all_predictions.append(seq_predictions)
            if return_probabilities:
                all_probabilities.append(seq_probabilities)
        
        results = [all_predictions]
        if return_probabilities:
            results.append(all_probabilities)
        if return_attention:
            results.append(all_attention)
        
        return tuple(results) if len(results) > 1 else results[0]

    def _apply_temporal_inertia(self, probabilities, smoothing_window=3, inertia_factor=0.5):
        """
        Smooth probabilities and apply temporal inertia to resist switching.
        
        Args:
            probabilities: (num_frames, num_classes) array of probabilities.
            smoothing_window: Size of the window for initial smoothing.
            inertia_factor: Factor to boost probabilities based on the previous frame's prediction.
            
        Returns:
            Adjusted probabilities.
        """
        num_frames, num_classes = probabilities.shape
        
        # 1. Initial Smoothing to reduce noise
        if smoothing_window > 1:
            smoothed_probs = np.zeros_like(probabilities)
            for i in range(num_classes):
                smoothed_probs[:, i] = np.convolve(probabilities[:, i], np.ones(smoothing_window)/smoothing_window, mode='same')
        else:
            smoothed_probs = probabilities.copy()
        
        # 2. Apply Temporal Inertia
        adjusted_probs = smoothed_probs.copy()
        
        for i in range(1, num_frames):
            # Boost current frame probabilities based on previous frame's adjusted probabilities
            adjusted_probs[i] = adjusted_probs[i] + inertia_factor * adjusted_probs[i-1]
            
            # Re-normalize probabilities for the current frame
            frame_sum = np.sum(adjusted_probs[i])
            if frame_sum > 0:
                adjusted_probs[i] /= frame_sum
            
        return adjusted_probs

    def evaluate(self, x_test, y_test, return_report=True):
        """
        Evaluate model performance on test sequences.
        
        Args:
            x_test: Test sequences
            y_test: Test frame-level labels
            return_report: Whether to return classification report
        
        Returns:
            accuracy: Frame-level accuracy
            report: (optional) Classification report dict
        """
        predictions = self.predict_frames(x_test, return_probabilities=False)
        
        # Flatten predictions and targets
        all_preds = []
        all_targets = []
        
        for seq_pred, seq_target in zip(predictions, y_test):
            all_preds.extend(seq_pred)
            
            # Convert targets to class indices if needed
            if seq_target.ndim == 2:  # One-hot encoded
                all_targets.extend(np.argmax(seq_target, axis=1))
            else:
                all_targets.extend(seq_target)
        
        accuracy = accuracy_score(all_targets, all_preds)
        
        if return_report:
            report = classification_report(
                all_targets, all_preds,
                target_names=self.class_names,
                output_dict=True
            )
            return accuracy, report
        
        return accuracy
    
    def plot_history(self, figsize=(12, 4)):
        """Plot training history"""
        if not self.history['train_loss']:
            print("No training history to plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # Loss plot
        ax1.plot(self.history['train_loss'], label='Train Loss')
        if self.history['val_loss']:
            ax1.plot(self.history['val_loss'], label='Val Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.set_title('Training and Validation Loss')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Accuracy plot
        ax2.plot(self.history['train_acc'], label='Train Acc')
        if self.history['val_acc']:
            ax2.plot(self.history['val_acc'], label='Val Acc')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Accuracy')
        ax2.set_title('Training and Validation Accuracy')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def _check_fitted(self):
        if self.model is None:
            raise RuntimeError("Model not fitted. Call fit() first.")
    
    def save_model(self, path):
        """Save the model to disk."""
        if self.model is None:
            raise RuntimeError("No model to save. Train a model first.")
        torch.save(self.model, path)
        if self.verbose:
            print(f"Model saved to {path}")
    
    def load_model(self, path):
        """Load a model from disk."""
        self.model = torch.load(path, map_location=self.device, weights_only=False)
        self.model.eval()
        
        if hasattr(self.model, 'num_classes') and self.num_classes != self.model.num_classes:
            self.num_classes = self.model.num_classes
        if hasattr(self.model, 'num_joint_features') and self.input_size != self.model.num_joint_features:
            self.input_size = self.model.num_joint_features
            
        if self.verbose:
            print(f"Model loaded from {path}")