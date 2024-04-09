import cv2

cap = cv2.VideoCapture('/home/hyunuklim/video/GX010094_ALTA787042484087914200.MP4')
ret, frame = cap.read()

if ret:
   cv2.imwrite('output_image.jpg', frame)

cap.release()
