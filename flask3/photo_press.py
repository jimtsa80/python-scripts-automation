# -*- coding: utf-8 -*-

import os
import glob
import sys
import csv
from pandas.io.excel import ExcelWriter
import pandas as pd
from PIL import Image
# from itertools import izip
from pyexiv2 import ImageMetadata, ExifTag


class Photo_press:
	def __init__(self):
		self.phtab = open("photo_tab.csv", "w")
		self.photo_sheet = csv.writer(self.phtab)
		self.photo_sheet.writerow(["ArticleID",	"PhotoID", "PhotoSize", "PageSize",	"Sponsor", "Touchpoint", "Percentage", "Double", "Hits"])
		self.imgID = []
		self.imsz1 = []
		self.imsz2 = []

	def getSize1(self, path):

		with open('pages.txt', 'r') as rf:
			reader = csv.reader(rf, delimiter='\t', quotechar='"')
			for row in reader:
				imgpath = '/'.join(row[1:4])
				img = os.path.realpath(path)+'/'+imgpath+'.jpg'
				try:
					im = Image.open(img)
				except IOError:
					not_found_images = open('not_found_images.txt','w')
					not_found_images.write(imgpath[imgpath.rfind('/')+1:] +"\t"+ 'not found -----> '+row[0])
					print(imgpath[imgpath.rfind('/')+1:] +"\t"+ 'not found -----> '+row[0])
					
					continue
				size = im.size
				self.imsz1.append(str(size[0])+'x'+str(size[1]))
				#print(imgpath[imgpath.rfind('/')+1:] +"\t"+ imsz)
				#not_found_images.close()
		
		return self.imsz1
				
	def getSize2(self, path):
		onlyfiles = [ f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)) ]
		
		for img in onlyfiles:
			try:
				im = Image.open(os.path.join(path,img))
			except IOError:
				print(imgpath[imgpath.rfind('/')+1:] +"\t"+ 'not found')
				continue
			size = im.size
			self.imgID.append(int(img.replace('.jpg', '')))
			self.imsz2.append(str(size[0])+'x'+str(size[1]))
			#print(img +"\t"+ imsz)
			#print(img.replace('.jpg', ''), str(size[0])+'x'+str(size[1]))
		
		return self.imgID, self.imsz2

	def photo_tab_creator(self):
		artID = []
		im_pend = open('im_pending.txt','w')
		with open('press_results.csv', 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			for row in reader:
				if row[7] == 'P':
					if row[0] != 'ArtID':
						artID.append(row[0])
		
		for a, b, c, d in zip(artID, sorted(self.imgID, key=int), self.imsz2, self.imsz1):
			im_pend.write(str(a) + "\t" + str(b) + "\t" + str(c) + "," + str(d) + '\n')
			if int(d.split('x')[0]) > 700:
				self.photo_sheet.writerow([a, b, c, d, '', '', '', '1', '',])
			else:
				self.photo_sheet.writerow([a, b, c, d, '', '', '', '', '',])
			
		im_pend.close()
		self.phtab.close()
	
	def metadata(self, folder):
		with open('im_pending.txt','r') as inputfile:
			metadataurls = inputfile.readlines()
			for meta in metadataurls:
				
				imgid = meta.split('\t')[1]
				artid = meta.split('\t')[0]
				imgurl = meta.split('\t')[2].strip()
				
				metadata = ImageMetadata(os.path.join(folder, imgid+'.jpg'))
				metadata.read()
				metadata["Exif.Photo.ImageUniqueID"] = artid
				metadata["Exif.Image.DocumentName"] = imgurl
				metadata.write()
		print('Metadata ready')

# if __name__ == "__main__":

# 	ph_press = Photo_press()

# 	ph_press.getSize2(sys.argv[1])
# 	ph_press.getSize1(sys.argv[2])
# 	ph_press.photo_tab_creator()
# 	ph_press.metadata()

# 	csvs = ['art_tab.csv', 'text_tab.csv', 'photo_tab.csv']

# 	with ExcelWriter(str(sys.argv[1]).replace('Photos','')+'_final.xlsx') as ew:
# 		for csv in csvs:
# 			if 'art' in csv:
# 				pd.read_csv(csv, encoding='utf-8', usecols = ['ArtID', 'Newspaper', 'Title','Date',	'WC','PN','Front/Back']).to_excel(ew, sheet_name=csv.split('.')[0], index=None)
# 			else:
# 				pd.read_csv(csv, encoding='utf-8', ).to_excel(ew, sheet_name=csv.split('.')[0], index=None)
	
