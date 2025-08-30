#!/usr/bin/env python3
# GIMP "*.gpl" palette to Adobe Photoshop "*.act" palette converter
#
# How to use:
#   python gpl_to_act.py input.gpl output.act
#
# The script will create a standard ACT file with up to 256 colors.
# If the palette has fewer than 256 colors, it will be padded with black.

import os
import re
import sys
from struct import pack

def parse_gpl_file(filename):
    """Parse a GIMP palette file and return a list of RGB tuples."""
    colors = []
    with open(filename, 'r', encoding='utf-8') as f:
        # Skip header lines until we find the color data
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Look for lines with RGB values (3 or 4 numbers)
            parts = re.split(r'\s+', line.strip())
            try:
                # Try to extract 3 or 4 numbers (RGB or RGBA)
                nums = [int(x) for x in parts if x.isdigit()][:3]
                if len(nums) >= 3:
                    # Ensure values are in 0-255 range
                    r, g, b = [max(0, min(255, x)) for x in nums[:3]]
                    colors.append((r, g, b))
            except (ValueError, IndexError):
                continue
    return colors

def create_act_file(colors, output_filename):
    """Create an ACT file from a list of RGB tuples."""
    with open(output_filename, 'wb') as f:
        # Write RGB values
        for r, g, b in colors[:256]:  # ACT format supports max 256 colors
            f.write(pack('3B', r, g, b))
        
        # If we have less than 256 colors, pad with black
        for _ in range(256 - len(colors)):
            f.write(pack('3B', 0, 0, 0))
        
        # Add color count for CS2 compatibility (optional, but some apps expect this)
        if len(colors) > 0 and len(colors) < 256:
            f.write(pack('>H', len(colors)))

def main():
    if len(sys.argv) != 3:
        print("Usage: python gpl_to_act.py input.gpl output.act")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    try:
        colors = parse_gpl_file(input_file)
        if not colors:
            print("Error: No valid colors found in the GPL file.")
            sys.exit(1)
            
        create_act_file(colors, output_file)
        print(f"Successfully converted {len(colors)} colors to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()