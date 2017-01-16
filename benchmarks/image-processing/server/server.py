# USAGE
# python detect_barcode.py --image images/barcode_01.jpg

# import the necessary packages
import numpy as np
import argparse
import cv2
import datetime
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/file_upload', methods=['GET', 'POST'])
def file_upload():
	start = time.time()
	image = request.files.get('image', '')
	imageval = image.read()
	duration = sift(imageval)
	#duration = detect_barcode(imageval)
	end = time.time()
	return str(end - start)

def sift(imageval):
	file_bytes = np.asarray(bytearray(imageval), dtype=np.uint8)
        img_data_ndarray = cv2.imdecode(file_bytes, cv2.CV_LOAD_IMAGE_UNCHANGED)
	gray = cv2.cvtColor(img_data_ndarray, cv2.COLOR_BGR2GRAY)
	#surf = cv2.SURF(400)
	sift = cv2.SIFT(40)
	kp, des = sift.detectAndCompute(gray,None)
	#kp, des = surf.detectAndCompute(gray,None)
	#print len(kp)
	
def surf(imageval):
	file_bytes = np.asarray(bytearray(imageval), dtype=np.uint8)
        img_data_ndarray = cv2.imdecode(file_bytes, cv2.CV_LOAD_IMAGE_UNCHANGED)
	gray = cv2.cvtColor(img_data_ndarray, cv2.COLOR_BGR2GRAY)
	surf = cv2.SURF(40)
	#sift = cv2.SIFT(40)
	#kp, des = sift.detectAndCompute(gray,None)
	kp, des = surf.detectAndCompute(gray,None)
	#print len(kp)
	



def detect_barcode(imageval):


	# load the image and convert it to grayscale

	file_bytes = np.asarray(bytearray(imageval), dtype=np.uint8)
        img_data_ndarray = cv2.imdecode(file_bytes, cv2.CV_LOAD_IMAGE_UNCHANGED)
	gray = cv2.cvtColor(img_data_ndarray, cv2.COLOR_BGR2GRAY)

	# compute the Scharr gradient magnitude representation of the images
	# in both the x and y direction
	gradX = cv2.Sobel(gray, ddepth = cv2.cv.CV_32F, dx = 1, dy = 0, ksize = -1)
	gradY = cv2.Sobel(gray, ddepth = cv2.cv.CV_32F, dx = 0, dy = 1, ksize = -1)

	# subtract the y-gradient from the x-gradient
	gradient = cv2.subtract(gradX, gradY)
	gradient = cv2.convertScaleAbs(gradient)

	# blur and threshold the image
	blurred = cv2.blur(gradient, (9, 9))
	(_, thresh) = cv2.threshold(blurred, 225, 255, cv2.THRESH_BINARY)

	# construct a closing kernel and apply it to the thresholded image
	kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
	closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

	# perform a series of erosions and dilations
	closed = cv2.erode(closed, None, iterations = 4)
	closed = cv2.dilate(closed, None, iterations = 4)

	# find the contours in the thresholded image, then sort the contours
	# by their area, keeping only the largest one
	(cnts, _) = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL,
		cv2.CHAIN_APPROX_SIMPLE)
	c = sorted(cnts, key = cv2.contourArea, reverse = True)[0]

	# compute the rotated bounding box of the largest contour
	rect = cv2.minAreaRect(c)
	box = np.int0(cv2.cv.BoxPoints(rect))

	# draw a bounding box arounded the detected barcode and display the
	# image
	cv2.drawContours(img_data_ndarray, [box], -1, (0, 255, 0), 3)
	# cv2.imshow("Image", image)
	#cv2.imwrite("uploads/output-"+ datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")  +".jpg",image)
	# cv2.waitKey(0)

	#outputfile = "uploads/output-" + time.strftime("%H:%M:%S") + ".jpg"
	outputfile = "uploads/output.jpg"

	cv2.imwrite(outputfile,img_data_ndarray)



if __name__ == '__main__':
	print 'server started ...'
        app.run(host= '0.0.0.0',port=8080)
