import torch
import torch.nn as nn
import torch.nn.functional as F

class TemporalAttention(nn.Module):
    """Attention over time frames"""
    def __init__(self, hidden_size):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1)
        )
    
    def forward(self, gru_outputs, mask=None):
        # gru_outputs: (batch, seq_len, hidden_size)
        scores = self.attention(gru_outputs)  # (batch, seq_len, 1)
        
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(-1) == 0, -1e9)
        
        weights = F.softmax(scores, dim=1)
        context = torch.sum(weights * gru_outputs, dim=1)
        
        return context, weights.squeeze(-1)


class JointAttention(nn.Module):
    """Attention over joint pair features"""
    def __init__(self, num_joint_features):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(num_joint_features, num_joint_features // 2),
            nn.ReLU(),
            nn.Linear(num_joint_features // 2, num_joint_features),
            nn.Sigmoid()  # Soft gating
        )
    
    def forward(self, x):
        # x: (batch, seq_len, num_joint_features)
        weights = self.attention(x)  # Learn importance of each joint pair
        return x * weights, weights


class PoseGRUModel(nn.Module):
    def __init__(
        self,
        num_joint_features,  # Number of cosine distance features
        hidden_size=128,
        num_layers=2,
        num_classes=10,      # Number of pose classes
        dropout=0.3,
        use_joint_attention=True,
        use_temporal_attention=True
    ):
        super().__init__()
        
        self.use_joint_attention = use_joint_attention
        self.use_temporal_attention = use_temporal_attention
        
        # Optional: Joint-level attention (which joint pairs matter)
        if use_joint_attention:
            self.joint_attention = JointAttention(num_joint_features)
        
        # Feature projection
        self.input_projection = nn.Sequential(
            nn.Linear(num_joint_features, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # Bidirectional GRU for temporal modeling
        self.gru = nn.GRU(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        # Temporal attention
        if use_temporal_attention:
            self.temporal_attention = TemporalAttention(hidden_size * 2)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes)
        )
    
    def forward(self, x, lengths=None):
        """
        x: (batch, num_frames, num_joint_features)
        lengths: actual sequence lengths (optional, for variable length)
        """
        batch_size, num_frames, num_features = x.shape
        
        # Joint attention - which joint pairs are important
        joint_weights = None
        if self.use_joint_attention:
            x, joint_weights = self.joint_attention(x)
        
        # Project features
        x = self.input_projection(x)
        
        # Temporal modeling with GRU
        gru_out, _ = self.gru(x)  # (batch, num_frames, hidden*2)
        
        # Temporal attention - which frames are important
        temporal_weights = None
        if self.use_temporal_attention:
            context, temporal_weights = self.temporal_attention(gru_out)
        else:
            context = gru_out[:, -1, :]  # Just use last frame
        
        # Classify
        logits = self.classifier(context)
        
        return logits, temporal_weights, joint_weights