#!/bin/bash

# Script to create default PNG launcher icons for Android
# Navigate to the project directory
cd /home/gstenger/Documents/my-pricer

# Create directories if they don't exist
mkdir -p android/app/src/main/res/mipmap-mdpi
mkdir -p android/app/src/main/res/mipmap-hdpi
mkdir -p android/app/src/main/res/mipmap-xhdpi
mkdir -p android/app/src/main/res/mipmap-xxhdpi
mkdir -p android/app/src/main/res/mipmap-xxxhdpi

# Create a simple default icon using ImageMagick
# Different sizes for different densities
convert -size 48x48 xc:transparent -fill "#3498db" -draw "circle 24,24 24,4" android/app/src/main/res/mipmap-mdpi/ic_launcher.png
convert -size 72x72 xc:transparent -fill "#3498db" -draw "circle 36,36 36,6" android/app/src/main/res/mipmap-hdpi/ic_launcher.png
convert -size 96x96 xc:transparent -fill "#3498db" -draw "circle 48,48 48,8" android/app/src/main/res/mipmap-xhdpi/ic_launcher.png
convert -size 144x144 xc:transparent -fill "#3498db" -draw "circle 72,72 72,12" android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png
convert -size 192x192 xc:transparent -fill "#3498db" -draw "circle 96,96 96,16" android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png

# Create round icons (same as regular but with different name)
cp android/app/src/main/res/mipmap-mdpi/ic_launcher.png android/app/src/main/res/mipmap-mdpi/ic_launcher_round.png
cp android/app/src/main/res/mipmap-hdpi/ic_launcher.png android/app/src/main/res/mipmap-hdpi/ic_launcher_round.png
cp android/app/src/main/res/mipmap-xhdpi/ic_launcher.png android/app/src/main/res/mipmap-xhdpi/ic_launcher_round.png
cp android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png android/app/src/main/res/mipmap-xxhdpi/ic_launcher_round.png
cp android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_round.png

echo "Default icons created successfully!"
