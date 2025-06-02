#!/bin/bash

# Script to convert all PBM launcher icons to PNG format
# Navigate to the project directory
cd /home/gstenger/Documents/my-pricer

# Process each mipmap directory
for dir in android/app/src/main/res/mipmap-*; do
  echo "Processing directory: $dir"
  
  # Convert ic_launcher.pbm to PNG if it exists
  if [ -f "$dir/ic_launcher.pbm" ]; then
    echo "Converting $dir/ic_launcher.pbm to PNG"
    convert "$dir/ic_launcher.pbm" "$dir/ic_launcher.png"
    rm "$dir/ic_launcher.pbm"
  fi
  
  # Convert ic_launcher_round.pbm to PNG if it exists
  if [ -f "$dir/ic_launcher_round.pbm" ]; then
    echo "Converting $dir/ic_launcher_round.pbm to PNG"
    convert "$dir/ic_launcher_round.pbm" "$dir/ic_launcher_round.png"
    rm "$dir/ic_launcher_round.pbm"
  fi
done

echo "Conversion complete!"
