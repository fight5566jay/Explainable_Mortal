"""
Generate a Mortal model with randomly initialized parameters.
This can be useful for testing, debugging, or creating baseline comparisons.
"""

import torch
import argparse
from os import path, makedirs
from datetime import datetime
from model import Brain, DQN, AuxNet
from config import config

    


def generate_random_mortal_model(
    output_path='built/models/random_mortal.pth',
    version=None,
    conv_channels=None,
    num_blocks=None,
    seed=None
):
    """
    Generate and save a Mortal model with random parameters.
    
    Args:
        output_path: Path where to save the model
        version: Model version (default from config)
        conv_channels: Number of convolutional channels (default from config)
        num_blocks: Number of ResNet blocks (default from config)
        seed: Random seed for reproducibility (optional)
    
    Returns:
        Dictionary containing the model state
    """
    
    # Use config values if not specified
    if version is None:
        version = config['control']['version']
    if conv_channels is None:
        conv_channels = config['resnet']['conv_channels']
    if num_blocks is None:
        num_blocks = config['resnet']['num_blocks']
    
    # Set random seed if provided
    if seed is not None:
        torch.manual_seed(seed)
        print(f"Random seed set to: {seed}")
    
    print("=== Generating Random Mortal Model ===\n")
    print(f"Model configuration:")
    print(f"  Version: {version}")
    print(f"  Conv channels: {conv_channels}")
    print(f"  Num blocks: {num_blocks}")
    print(f"  Output path: {output_path}")
    print()
    
    # Get device for scaler
    device = torch.device(config['control']['device'])
    
    # Create models with random initialization
    print("Creating models...")
    mortal = Brain(version=version, conv_channels=conv_channels, num_blocks=num_blocks)
    dqn = DQN(version=version)
    aux_net = AuxNet((4,))
    
    # Count parameters
    mortal_params = sum(p.numel() for p in mortal.parameters())
    dqn_params = sum(p.numel() for p in dqn.parameters())
    aux_params = sum(p.numel() for p in aux_net.parameters())
    
    print(f"✓ Models created")
    print(f"  Mortal parameters: {mortal_params:,}")
    print(f"  DQN parameters: {dqn_params:,}")
    print(f"  Aux parameters: {aux_params:,}")
    print(f"  Total parameters: {mortal_params + dqn_params + aux_params:,}")
    print()
    
    # Create optimizer and scheduler (with structure matching train.py)
    from torch import optim, nn
    from lr_scheduler import LinearWarmUpCosineAnnealingLR
    
    # Build parameter groups exactly as train.py does
    all_models = (mortal, dqn, aux_net)
    
    decay_params = []
    no_decay_params = []
    for model in all_models:
        params_dict = {}
        to_decay = set()
        for mod_name, mod in model.named_modules():
            for name, param in mod.named_parameters(prefix=mod_name, recurse=False):
                params_dict[name] = param
                if isinstance(mod, (nn.Linear, nn.Conv1d)) and name.endswith('weight'):
                    to_decay.add(name)
        decay_params.extend(params_dict[name] for name in sorted(to_decay))
        no_decay_params.extend(params_dict[name] for name in sorted(params_dict.keys() - to_decay))
    
    param_groups = [
        {'params': decay_params, 'weight_decay': config['optim']['weight_decay']},
        {'params': no_decay_params},
    ]
    
    optimizer = optim.AdamW(
        param_groups,
        lr=1,
        weight_decay=0,
        betas=config['optim']['betas'],
        eps=config['optim']['eps']
    )
    scheduler = LinearWarmUpCosineAnnealingLR(optimizer, **config['optim']['scheduler'])
    
    # Create scaler for mixed precision training
    from torch.cuda.amp import GradScaler
    scaler = GradScaler(device.type, enabled=config['control']['enable_amp'])
    
    # Create state dictionary
    state = {
        'mortal': mortal.state_dict(),
        'current_dqn': dqn.state_dict(),
        'aux_net': aux_net.state_dict(),
        'optimizer': optimizer.state_dict(),
        'scheduler': scheduler.state_dict(),
        'scaler': scaler.state_dict(),
        'steps': 0,
        'timestamp': datetime.now().timestamp(),
        'best_perf': {
            'avg_rank': 4.0,  # Worst possible rank
            'avg_pt': -135.0,  # Worst possible points
        },
        'config': config,
    }
    
    #If output_path is not exist, mkdir
    output_dir = path.dirname(output_path)
    if not path.exists(output_dir):
        makedirs(output_dir)

    # Save the model
    print(f"Saving random model to: {output_path}")
    torch.save(state, output_path)
    print(f"✓ Model saved successfully")
    print()
    
    # Verify by loading
    print("Verifying saved model...")
    loaded_state = torch.load(output_path, weights_only=True, map_location='cpu')
    print(f"✓ Model loaded successfully")
    print(f"  Timestamp: {datetime.fromtimestamp(loaded_state['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Steps: {loaded_state['steps']:,}")
    print(f"  Config version: {loaded_state['config']['control']['version']}")
    print()
    
    # Show some statistics about the random parameters
    print("Random parameter statistics:")
    mortal_weights = torch.cat([p.flatten() for p in mortal.parameters()])
    print(f"  Mortal weights - mean: {mortal_weights.mean():.6f}, std: {mortal_weights.std():.6f}")
    print(f"                   min: {mortal_weights.min():.6f}, max: {mortal_weights.max():.6f}")
    
    dqn_weights = torch.cat([p.flatten() for p in dqn.parameters()])
    print(f"  DQN weights    - mean: {dqn_weights.mean():.6f}, std: {dqn_weights.std():.6f}")
    print(f"                   min: {dqn_weights.min():.6f}, max: {dqn_weights.max():.6f}")
    
    print("\n=== Random Model Generation Complete ===")
    
    return state


def main():
    parser = argparse.ArgumentParser(description='Generate a random-parameter Mortal model')
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='built/models/random_mortal.pth',
        help='Output path for the model file'
    )
    parser.add_argument(
        '--version',
        type=int,
        default=None,
        help='Model version (default: from config)'
    )
    parser.add_argument(
        '--conv-channels',
        type=int,
        default=None,
        help='Number of convolutional channels (default: from config)'
    )
    parser.add_argument(
        '--num-blocks',
        type=int,
        default=None,
        help='Number of ResNet blocks (default: from config)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for reproducibility (default: no seed)'
    )
    
    args = parser.parse_args()
    
    generate_random_mortal_model(
        output_path=args.output,
        version=args.version,
        conv_channels=args.conv_channels,
        num_blocks=args.num_blocks,
        seed=args.seed
    )


if __name__ == '__main__':
    main()
