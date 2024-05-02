#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import csv
import sys
import codecs
import shutil
import pandas as pd
from random import randint
try:
	from urlparse import urlparse
except:
	from urllib.parse import urlparse
from datetime import date, timedelta
from collections import OrderedDict
from collections import Counter

# reload(sys)  
# sys.setdefaultencoding('utf8')

class Social_parser:
	def __init__(self, ontologyKws):
		self.artID = 0
		self.textID = 0
		self.exceptions = []
		self.value1text = []
		if ontologyKws != '':
			self.textab = open("text_tab.csv", "w", encoding='utf-8')
			self.text_sheet = csv.writer(self.textab)

		self.kwds = {}
		self.secondary = {}
		self.unwanted = {}
		self.textab = open("text_tab.csv", "w")
		self.text_sheet = csv.writer(self.textab)

		if ontologyKws != "":
			try:
				ontologyI = open(ontologyKws, 'r', encoding='utf-8', errors='ignore')
				ontology = ontologyI.readlines()
				for item in ontology:
					item = item.replace('\n', '')
					item = item.replace('\xef\xbb\xbf', '')
					if not item.startswith('\t'):
						team = item
					else:
						if item.startswith('#') is False and item.startswith('	$$$ ') is False and item.startswith('	*** ') is False:
							item = item.split('<=')
							official = team + '--->>>' + item[0].strip()
							self.kwds[official] = []
							alt = item[1].strip()
							alist = alt.split('|')
							for a in alist:
								a = a.strip()
								if a.find('^') >= 0:
									a = a.replace('^', ' ')
								# print(a)
								self.kwds[official].append(a.lower())
						elif item.startswith('	$$$ ') is True:
							#item = item.replace('$$$ ', '')
							item = item.split('<=')
							official = team + '--->>>' + item[0].strip()
							official = official.replace('$$$ ', '')
							self.secondary[official] = []
							alt = item[1].strip()
							alist = alt.split('|')
							for a in alist:
								a = a.strip()
								if a.find('^') >= 0:
									a = a.replace('^', ' ')
								self.secondary[official].append(a.lower())
						elif item.startswith('	*** ') is True:
							#item = item.replace('*** ', '')
							item = item.split('<=')
							official = team + '--->>>' + item[0].strip()
							official = official.replace('*** ', '')
							self.unwanted[official] = []
							alt = item[1].strip()
							alist = alt.split('|')
							for a in alist:
								a = a.strip()
								if a.find('^') >= 0:
									a = a.replace('^', ' ')
								self.unwanted[official].append(a.lower())
						else:
							continue
				ontologyI.close()
			except IOError:
				print(' ...wrong ontology file name...')

	def post_analyzer(self, post):
		rows = {}
		allkwds = ''
		post = post.lower()

		for k1, v1 in self.kwds.items():
			for k2, v2 in self.secondary.items():
				for k3, v3 in self.unwanted.items():
					for value1 in v1:
						for value2 in v2:
							for value3 in v3:
								post = post.replace(value3, "")
								if value1 in post and value2 in post and k1.split('--->>>')[0] == k2.split('--->>>')[0]:
									if " " in value1:
										if " " in value2:
											rows[k1] = value1
											allkwds += value1

										else:
											rows[k1] = value1
											allkwds += value1

									else:
										if " " in value2:
											rows[k1] = value1
											allkwds += value1

										else:
											rows[k1] = value1
											allkwds += value1

									post = post.replace(value1, "")
								else:
									pass

		return rows

	def get_mention(self, infile, delimiter):

		project = ''
		for_printing = []
		try:
			with codecs.open(infile, 'rU', 'utf-8', errors='replace') as myfile:
				data = myfile.read()
				#clean file first if dirty
				if data.count( '\x00' ):
					print('Cleaning... ' + str(infile))
					with codecs.open('temp.csv.tmp', 'w', 'utf-8') as of:
						for line in data:
							of.write(line.replace('\x00', ''))
					shutil.move(os.path.join(os.getcwd(), 'temp.csv.tmp'), os.path.join(os.getcwd(), str(infile)))
					print("Done with cleaning")
			
			if 'press' in infile:
				project = 'press'
				artab = open("art_tab.csv", "w")
				article_sheet = csv.writer(artab)
				article_sheet.writerow(["ArtID", "Newspaper", "Title", "Date", "WC", "PN", "Front/Back", "Photo"])
			else:
				try:
					project = infile.split('_')[5].split('.')[0]
					project = re.sub( r"([A-Z])", r" \1", project).split()[0]
				except IndexError as e:
					print("The filename must have this format eg '2017_12_01-2017_12_15_twitterNZCricket'")
					for_printing.append("The results are wrong! The filename must have this format eg. '2017_12_01-2017_12_15_twitterNZCricket'" + ' ' + '1')

			text_file = codecs.open(infile, 'rb', encoding='utf-8', errors='replace')
			textfound = False
			rowsCount = 0
			curRow = 0
			fileoutput = open('stats.txt','w')
			
			if project == 'press':
				fileoutput2 = open('not_found.txt','w')
				pages = open('pages.txt','w')
			

			if 'press' in infile:
				delimiter = 'comma'
				reader = csv.reader(text_file, delimiter=',', quotechar='"')

			if delimiter == "comma":
				reader = csv.reader(text_file, delimiter=',', quotechar='"')
			else:
				reader = csv.reader(text_file, delimiter=';', quotechar='"')

			self.text_sheet.writerow(["ArtID", "TextID", "Mention", "Keyword"])

			for line in reader:
				rowsCount += 1

			text_file.seek(0)

			for row in reader:
				curRow += 1
				print(str(curRow) + " / " + str(rowsCount))
				textfound = False
				try:
					if row[0] == 'ArtID' or row[0] == 'artid' or row[0] == 'id':#ArtID , Post ID
						continue
					col_id = row[0]
					if project == 'twitter':
						uri = urlparse(row[2])
						user = uri[2].split('/')[1].lower()
						user2 = user
						col_game = row[5].lower().strip()
						# try:
						# 	new_coding = 'UTF-8'
						# 	post = col_game
						# 	post = post.encode('ascii', 'replace')
						# 	post = re.sub('[^A-z0-9@#_ ]', '', post).lower()
						# except Exception as e:
						# 	print(e.message, e.args)

					elif project == 'instagram':
						uri = urlparse(row[2])
						user = row[1].lower()
						user2 = user
						col_game = row[5].lower().strip()
						
						# try:
						# 	new_coding = 'UTF-8'
						# 	post = col_game
						# 	post = post.encode('ascii', 'replace')
						# 	post = re.sub('[^A-z0-9@# ]', '', post).lower()
						# except Exception as e:
						# 	print(e.message, e.args)

					elif project == 'press':
						artID = row[0]
						np = row[1]
						title = row[2]
						date = row[3]
						post = row[4].replace('\n', ' ').strip().lower()
						pn = row[5]
						frbk = row[6]
						photo = row[7]
						#print col_game
						if '__' in post:
							wc = randint(50, 500)
						elif len(post.split()) == 2 and post.split()[1] == 'photo':
							wc = int(post.split()[0])
						else:
							wc = len(post.split())
						user = ' '
						user2 = user
						if photo == 'P':
							dt = date.split('-')
							pages.write(artID + "\t" + np + "\t" + str(dt[2]) + str(dt[1]) + "\t" + str(pn) + '\n')
						
						

						# try:
						# 	new_coding = 'UTF-8'
						# 	post = col_game
						# 	post = post.encode('ascii', 'replace')
						# 	post = re.sub('[^A-z0-9@# ]', '', post).lower()
						# except Exception as e:
						# 	print e.message, e.args



					else:
						uri = ''
						user = ''
						user2 = user
						col_game = row[5].lower().strip()
						# try:
						# 	new_coding = 'UTF-8'
						# 	post = col_game
						# 	post = post.encode('ascii', 'replace')
						# 	post = re.sub('[^A-z0-9@# ]', '', post).lower()
						# except Exception as e:
						# 	print(e.message, e.args)
				except:
					continue

				post = col_game

				rows = self.post_analyzer(post)

				for k1, v1 in self.kwds.items():
					for value1 in v1:
						if "." in value1:
							fvalues1 = re.compile(value1)
							fvalues1 = fvalues1.findall(post)
							for value11 in fvalues1:
								self.kwds[k1].append(value11.lower())
				for k2, v2 in self.secondary.items():
					for value2 in v2:
						if "." in value2:
							fvalues2 = re.compile(value2)
							fvalues2 = fvalues2.findall(post)
							for value22 in fvalues2:
								self.secondary[k2].append(value22.lower())
				for k3, v3 in self.unwanted.items():
					for value3 in v3:
						if "." in value3:
							fvalues3 = re.compile(value3)
							fvalues3 = fvalues3.findall(post)
							for value33 in fvalues3:
								self.unwanted[k3].append(value33.lower())

				for k3, v3 in self.unwanted.items():
					v3.sort(key=lambda x: len(x.split()), reverse=True)
					for value3 in v3:
						post = post.replace(value3, "")

				for k1, v1 in self.kwds.items():
					v1.sort(key=lambda x: len(x.split()), reverse=True)
					for k2, v2 in self.secondary.items():
						v2.sort(key=lambda x: len(x.split()), reverse=True)
						for value1 in v1:
							for value2 in v2:
								if ((value1 in post and (value2 in post or value2 in user2.lower().replace('_', '')) and k1.split('--->>>')[0] == k2.split('--->>>')[0])) \
								or ((value1 in user2.lower() and (value2 in post or value2 in user2.lower().replace('_', '')) and k1.split('--->>>')[0] == k2.split('--->>>')[0])):
									textfound = True
									if " " in value1:
										fileoutput.write(value1 + " ||| " + value2 + " @ " + col_id + '\n')
										self.value1text.append(value1)
										if " " in value2:
											self.textID += 1
											if project == 'twitter' or project == 'facebook':
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1], col_game])
											elif project == 'press':
												
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1]])
											else:
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1], col_game])
										else:
											self.textID += 1
											if project == 'twitter' or project == 'facebook':
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1], col_game])
											elif project == 'press':
												
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1]])
											else:
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1], col_game])
									else:
										fileoutput.write(value1 + " ||| " + value2 + " @ " + col_id + '\n')
										self.value1text.append(value1)
										if " " in value2:
											self.textID += 1
											if project == 'twitter' or project == 'facebook':
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1], col_game])
											elif project == 'press':
												
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1]])
											else:
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1], col_game])
										else:
											self.textID += 1
											if project == 'twitter' or project == 'facebook':
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1], col_game])
											elif project == 'press':
												
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1]])
											else:
												self.text_sheet.writerow([col_id, self.textID, value1, k1.split('--->>>')[1], col_game])
									post = post.replace(value1, "")
									user2 = user2.replace(value1, "")
								else:
									pass

				if (textfound == True and project == 'press') or ('photo' in post and project == 'press'): 
					article_sheet.writerow([artID, np, title, date, wc, pn, frbk, photo])

				if textfound == False:
					self.textID += 1
					if project == 'press' and 'photo' not in post:
						fileoutput2.write(artID + ' ' + post + '\n')
					elif project == 'press' and 'photo' in post:
						pass
					else:
						pass
						#self.text_sheet.writerow([col_id, self.textID, 'photo', 'photo'])

			text_file.close()

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(exc_tb.tb_lineno, e)
			#exc = str(infile) + ' // csv line: ' + str(reader.line_num) + ' // script line: ' + str(exc_tb.tb_lineno) + ' // ' + str(e)
			#exceptions.append(exc)

		category = Counter(self.value1text)

		for key, value in category.items():
			for_printing.append(str(key) + ' ' + str(value))

		for_printing.sort(key = lambda x: int(x.split()[-1]), reverse=True)

		#fileoutput.close()
		if project == 'press':
			artab.close()
			fileoutput2.close()
			pages.close()

		return for_printing

if __name__ == "__main__":
	soc_parser = Social_parser(sys.argv[1])

	xlsx = pd.read_excel(sys.argv[2], index_col=None)
	xlsx.to_csv('press_results.csv', encoding='utf-8', index=False)

	soc_parser.get_mention('press_results.csv', 'comma')

	textab.close()