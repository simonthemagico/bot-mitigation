import cv2
import numpy as np
import tempfile

def extract_exterior_contour(piece_path: str):
    img = cv2.imread(piece_path, cv2.IMREAD_GRAYSCALE)
    
    # Threshold the image to get a binary image
    _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours by area and get the largest contour
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    largest_contour = contours[0]
    
    # Get bounding rectangle of the largest contour
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Crop the contour region
    cropped = img[y:y+h, x:x+w]
    
    # Create a blank canvas of the size of the cropped image
    blank = np.zeros_like(cropped)
    
    # Adjust contour points after cropping
    adjusted_contour = largest_contour - [x, y]
    
    # Draw the adjusted contour on the blank cropped image
    cv2.drawContours(blank, [adjusted_contour], -1, (255, 255, 255), 1)

    # Save the cropped contour image as png
    # cv2.imwrite('/tmp/piece-contour.jpg', blank)
    
    return blank

def find_puzzle_fit_area(bg_image_path: str, piece_image_path: str):
    bg_img = cv2.imread(bg_image_path)
    piece_contour = extract_exterior_contour(piece_image_path)
    
    piece_edges = cv2.Canny(piece_contour, 100, 200)
    bg_edges = cv2.Canny(bg_img, 100, 200)
    
    result = cv2.matchTemplate(bg_edges, piece_edges, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)

    # visualize the edges
    with tempfile.NamedTemporaryFile(suffix='.jpg') as f, tempfile.NamedTemporaryFile(suffix='.jpg') as f2:
        cv2.imwrite(f.name, piece_edges)
        cv2.imwrite(f2.name, bg_edges)
        print(f"Piece edges saved to {f.name}.")
        print(f"Background edges saved to {f2.name}.")

        # draw a rectangle around the matched region
        h, w = piece_edges.shape
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)
        cv2.rectangle(bg_img, top_left, bottom_right, (0, 0, 255), 2)
    
        return max_loc

def main():
    captcha_piece_file = 'files/captcha-piece-1.png'
    captcha_bg_file = 'files/captcha-bg-1.jpg'

    x, y = find_puzzle_fit_area(captcha_bg_file, piece_image_path=captcha_piece_file)
    print(f"Piece fits at x = {x} and y = {y}.")

if __name__ == '__main__':
   main()