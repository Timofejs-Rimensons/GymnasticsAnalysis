import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torch.nn.utils.rnn import pad_sequence
import numpy as np
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
from tqdm import tqdm

from models.ScoringGRUModel import ScoringGRUModel

class ScoringService:
    """
    Service for training and using a ScoringGRUModel for regression tasks.
    """
    
    def __init__(
        self,
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
        verbose=True,
        augment=True,
        augment_scale_range=(0.99, 1.01),
        model_path=None,
        use_joint_attention=True,
        use_temporal_attention=True,
        padding_mode='edge',
        num_outputs=1
    ):
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
        self.augment = augment
        self.augment_scale_range = augment_scale_range
        self.use_joint_attention = use_joint_attention
        self.use_temporal_attention = use_temporal_attention
        self.padding_mode = padding_mode
        self.num_outputs = num_outputs
        
        self.device = torch.device(
            device if device else ('cuda:0' if torch.cuda.is_available() else 'cpu')
        )
        
        if model_path:
            self.model = torch.load(model_path, weights_only=False)
            self.model.eval()
        else:
            self.model = None
        
        self.input_size = None
        self.history = {'train_loss': [], 'val_loss': []}

    def set_model(self, model):
        self.model = model.to(self.device)

    def set_hyperparameters(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def _build_model(self, input_size):
        self.input_size = input_size
        self.model = ScoringGRUModel(
            num_joint_features=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
            use_joint_attention=self.use_joint_attention,
            use_temporal_attention=self.use_temporal_attention,
            num_outputs=self.num_outputs
        ).to(self.device)

    def _create_windows(self, features, targets=None):
        num_frames = len(features)
        
        if num_frames < self.window_size:
            return [], []

        windows = []
        window_targets = []
        
        for i in range(0, num_frames - self.window_size + 1, self.stride):
            windows.append(features[i:i+self.window_size])
            if targets is not None:
                window_targets.append(np.mean(targets[i:i+self.window_size], axis=0))

        return windows, window_targets

    def _prepare_batch_windows(self, sequences, targets=None):
        all_windows = []
        all_targets = []
        
        for i, seq_features in enumerate(sequences):
            seq_targets = targets[i] if targets is not None else None
            windows, window_targets = self._create_windows(seq_features, seq_targets)
            all_windows.extend(windows)
            all_targets.extend(window_targets)
        
        return all_windows, all_targets

    def _augment_windows(self, windows):
        if not self.augment:
            return windows
        augmented = []
        low, high = self.augment_scale_range
        for window in windows:
            scale = np.random.uniform(low, high, size=window.shape).astype(window.dtype)
            augmented.append(window * scale)
        return augmented

    def fit(self, x_train, y_train, x_val=None, y_val=None):
        if self.model is None:
            input_size = x_train[0].shape[1]
            self._build_model(input_size)
        
        train_windows, train_targets = self._prepare_batch_windows(x_train, y_train)
        n_windows = len(train_windows)
        
        if self.verbose:
            print(f"Created {n_windows} training samples from {len(x_train)} sequences")
        
        val_windows, val_targets = (None, None)
        if x_val is not None:
            val_windows, val_targets = self._prepare_batch_windows(x_val, y_val)
            if self.verbose:
                print(f"Created {len(val_windows)} validation samples from {len(x_val)} sequences")
        
        criterion = nn.MSELoss()
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
            
            indices = np.random.permutation(n_windows)
            train_loss = 0
            
            for batch_start in range(0, n_windows, self.batch_size):
                batch_end = min(batch_start + self.batch_size, n_windows)
                batch_indices = indices[batch_start:batch_end]
                
                batch_windows = [train_windows[i] for i in batch_indices]
                batch_targets = [train_targets[i] for i in batch_indices]

                if self.augment:
                    batch_windows = self._augment_windows(batch_windows)

                batch_x = torch.tensor(np.array(batch_windows), dtype=torch.float32).to(self.device)
                batch_y = torch.tensor(batch_targets, dtype=torch.float32).to(self.device)
                
                optimizer.zero_grad()
                
                scores, _, _ = self.model(batch_x)
                
                loss = criterion(scores, batch_y)
                loss.backward()
                
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                
                train_loss += loss.item() * len(batch_y)
            
            train_loss /= n_windows
            self.history['train_loss'].append(train_loss)
            
            val_loss = 0
            if val_windows is not None:
                val_loss = self._evaluate_windows(val_windows, val_targets, criterion)
                self.history['val_loss'].append(val_loss)
                
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
                desc = f'Loss: {train_loss:.4f}'
                if val_windows is not None:
                    desc += f' | Val Loss: {val_loss:.4f}'
                epoch_iterator.set_postfix_str(desc)
        
        if best_model_state:
            self.model.load_state_dict(best_model_state)
        
        return self
    
    @torch.no_grad()
    def _evaluate_windows(self, windows, targets, criterion):
        self.model.eval()
        total_loss = 0
        
        for batch_start in range(0, len(windows), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(windows))
            
            batch_windows = windows[batch_start:batch_end]
            batch_targets = targets[batch_start:batch_end]

            batch_x = torch.tensor(np.array(batch_windows), dtype=torch.float32).to(self.device)
            batch_y = torch.tensor(batch_targets, dtype=torch.float32).to(self.device)
            
            scores, _, _ = self.model(batch_x)
            
            loss = criterion(scores, batch_y)
            total_loss += loss.item() * len(batch_y)
        
        return total_loss / len(windows)
    
    @torch.no_grad()
    def predict(self, x, return_attention=False):
        self._check_fitted()
        self.model.eval()
        
        all_scores = []
        all_attention = {'temporal': [], 'joint': []} if return_attention else None
        
        # Process in batches
        for batch_start in range(0, len(x), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(x))
            batch_sequences = x[batch_start:batch_end]

            padded_sequences = pad_sequence([torch.FloatTensor(s) for s in batch_sequences], batch_first=True)
            batch_x = padded_sequences.to(self.device)

            scores, temporal_weights, joint_weights = self.model(batch_x)
            all_scores.extend(scores.cpu().numpy())

            if return_attention:
                if temporal_weights is not None:
                    all_attention['temporal'].extend(temporal_weights.cpu().numpy())
                if joint_weights is not None:
                    all_attention['joint'].extend(joint_weights.cpu().numpy())
        
        results = [all_scores]
        if return_attention:
            results.append(all_attention)
        
        return tuple(results) if len(results) > 1 else results[0]

    @torch.no_grad()
    def predict_frames(self, x):
        self._check_fitted()
        if not hasattr(self.model, 'predict_frames'):
            raise NotImplementedError("The loaded model does not have a 'predict_frames' method.")
        self.model.eval()

        all_scores = []
        # x is a list of sequences
        for batch_start in range(0, len(x), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(x))
            batch_sequences = x[batch_start:batch_end]

            padded_sequences = pad_sequence([torch.FloatTensor(s) for s in batch_sequences], batch_first=True)
            batch_x = padded_sequences.to(self.device)

            scores = self.model.predict_frames(batch_x) # returns (batch, num_frames, num_outputs)
            
            # Unpad the results
            for i, seq in enumerate(batch_sequences):
                seq_len = len(seq)
                all_scores.append(scores[i, :seq_len, :].cpu().numpy())

        return all_scores

    def evaluate(self, x_test, y_test):
        predictions = self.predict(x_test)
        mse = mean_squared_error(y_test, predictions)
        return mse

    def plot_history(self, figsize=(8, 5)):
        if not self.history['train_loss']:
            print("No training history to plot")
            return
        
        plt.figure(figsize=figsize)
        plt.plot(self.history['train_loss'], label='Train Loss')
        if self.history['val_loss']:
            plt.plot(self.history['val_loss'], label='Val Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss (MSE)')
        plt.title('Training and Validation Loss')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()

    def _check_fitted(self):
        if self.model is None:
            raise RuntimeError("Model not fitted. Call fit() first.")

    def save_model(self, path):
        if self.model is None:
            raise RuntimeError("No model to save. Train a model first.")
        torch.save(self.model, path)
        if self.verbose:
            print(f"Model saved to {path}")
    
    def load_model(self, path):
        # Load the entire model object
        self.model = torch.load(path, map_location=self.device, weights_only=False)
        self.model.eval()
        
        # After loading the model, ensure the service's input_size is updated
        # to reflect the loaded model's architecture.
        # This assumes the loaded model (ScoringGRUModel) has a 'num_joint_features' attribute.
        if hasattr(self.model, 'num_joint_features') and self.input_size != self.model.num_joint_features:
            self.input_size = self.model.num_joint_features
            
        if self.verbose:
            print(f"Model loaded from {path} with input_size {self.input_size}")
