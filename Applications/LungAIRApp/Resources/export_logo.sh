#!/bin/bash

# Need inkscape, imagemagick, and icnsutils

set -e

inkscape --export-png=Images/Logo.png logo.svg -w 256 -h 256
inkscape --export-png=Images/LogoFull.png logo_plus_text.svg -w 128 -h 35
inkscape --export-png=Images/SplashScreen.png logo_plus_text.svg -w 640 -h 175

inkscape --export-png=Images/Logo.png logo.svg -w 256 -h 256
inkscape --export-png=Icons/Large/DesktopIcon.png logo.svg  -w 64 -h 64
inkscape --export-png=Icons/Medium/DesktopIcon.png logo.svg -w 32 -h 32
inkscape --export-png=Icons/Small/DesktopIcon.png logo.svg -w 16 -h 16
inkscape --export-png=Icons/XLarge/DesktopIcon.png logo.svg -w 128 -h 128

inkscape --export-png=Icons/DesktopIconTemp.png logo.svg -w 256 -h 256
convert -compress None Icons/DesktopIconTemp.png Icons/DesktopIcon.ico
png2icns Icons/DesktopIcon.icns Icons/DesktopIconTemp.png
rm Icons/DesktopIconTemp.png
