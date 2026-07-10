import cv2
import numpy as np

drawing = False  # Mouse state
ix, iy = -1, -1

def draw_mask(event, x, y, flags, param):
    global drawing, ix, iy

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            cv2.circle(mask_display, (x, y), 10, 255, -1)
            cv2.circle(mask, (x, y), 10, 255, -1)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        cv2.circle(mask_display, (x, y), 10, 255, -1)
        cv2.circle(mask, (x, y), 10, 255, -1)

# Load image
image_path = 'ola-0189.jpg'  # Replace with your image
image = cv2.imread(image_path)
mask = np.zeros(image.shape[:2], dtype=np.uint8)
mask_display = mask.copy()

cv2.namedWindow('Draw on Watermark')
cv2.setMouseCallback('Draw on Watermark', draw_mask)

print("[INFO] Draw over the watermark using your mouse. Press 'i' to inpaint or 'q' to quit.")

while True:
    preview = image.copy()
    preview[mask_display == 255] = (0, 0, 255)
    cv2.imshow('Draw on Watermark', preview)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('i'):  # Inpaint when 'i' is pressed
        # Feather the mask for smoother edges
        feathered_mask = cv2.GaussianBlur(mask, (21, 21), 0)
        feathered_mask = cv2.threshold(feathered_mask, 10, 255, cv2.THRESH_BINARY)[1]

        result = cv2.inpaint(image, feathered_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        cv2.imshow('Inpainted Result', result)
        cv2.imwrite('output_inpainted.jpg', result)
        print("[INFO] Inpainting complete. Saved as 'output_inpainted.jpg'.")

    elif key == ord('q'):
        break

cv2.destroyAllWindows()
