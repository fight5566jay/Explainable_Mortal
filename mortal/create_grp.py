#!/usr/bin/env python3

import torch
import torch.nn as nn
from datetime import datetime
from model import GRP
from config import config

def create_grp_model():
    """Create and save a GRP model with the configuration from config.toml"""
    
    # Get GRP configuration
    grp_config = config['grp']['network']
    hidden_size = grp_config['hidden_size']
    num_layers = grp_config['num_layers']
    
    print(f"Creating GRP model with hidden_size={hidden_size}, num_layers={num_layers}")
    
    # Create the model
    grp = GRP(hidden_size=hidden_size, num_layers=num_layers)
    
    # Create a dummy optimizer state (in case it's needed)
    optimizer = torch.optim.Adam(grp.parameters(), lr=1e-5)
    
    # Create the state dict in the expected format
    state = {
        'timestamp': datetime.now().timestamp(),
        'model': grp.state_dict(),
        'optimizer': optimizer.state_dict(),
        'steps': 0
    }
    
    # Save the model
    save_path = config['grp']['state_file']
    torch.save(state, save_path)
    print(f"GRP model saved to: {save_path}")
    
    # Verify the model can be loaded
    loaded_state = torch.load(save_path, weights_only=True, map_location=torch.device('cpu'))
    print("Model verification:")
    print(f"  Keys: {list(loaded_state.keys())}")
    print(f"  Model keys: {list(loaded_state['model'].keys())[:5]}...")  # Show first 5 keys
    print(f"  Timestamp: {datetime.fromtimestamp(loaded_state['timestamp'])}")

if __name__ == "__main__":
    create_grp_model()