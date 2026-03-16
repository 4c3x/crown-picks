"""
Generate PWA icons for Crown Picks
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """Create a simple crown icon."""
    # Create image with dark background
    img = Image.new('RGB', (size, size), color='#0a0a0f')
    draw = ImageDraw.Draw(img)
    
    # Draw crown emoji (simplified as text)
    try:
        # Try to use a system font
        font_size = int(size * 0.5)
        font = ImageFont.truetype("seguiemj.ttf", font_size)  # Windows emoji font
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Draw crown emoji
    crown_text = "👑"
    bbox = draw.textbbox((0, 0), crown_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - int(size * 0.1)
    
    draw.text((x, y), crown_text, font=font, fill='#ffd700')
    
    # Draw text below
    try:
        text_font = ImageFont.truetype("arial.ttf", int(size * 0.1))
    except:
        text_font = ImageFont.load_default()
    
    if size >= 256:
        label = "CROWN PICKS"
        label_bbox = draw.textbbox((0, 0), label, font=text_font)
        label_width = label_bbox[2] - label_bbox[0]
        label_x = (size - label_width) // 2
        label_y = y + text_height + int(size * 0.05)
        draw.text((label_x, label_y), label, font=text_font, fill='#ffd700')
    
    # Save
    img.save(filename, 'PNG')
    print(f"✅ Created {filename}")

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    create_icon(192, 'static/icon-192.png')
    create_icon(512, 'static/icon-512.png')
    print("✅ All icons created!")
