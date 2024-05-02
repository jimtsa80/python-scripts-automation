# -*- coding: utf-8 -*-

import glob
import sys
import os
import re
import time
import csv
from datetime import datetime as dt, timedelta
import pandas as pd
from pandas import *
# from pandas.api.types import is_datetimetz
import numpy as np
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import string
from requests import get
from io import BytesIO
from PIL import Image
import imagehash

#folder concat newfilename time
#folder multi
#folder web file
#folder press

class Xlsx_creator():
	def __init__(self):
		self.entries = []
		self.dfs = []
		self.wrong_brands = []
		self.wrong_locations = []


	def take_arguments(self, arg0, arg1, arg2=None, length=None):
		global csvfiles

		self.folder = arg0
		if arg1 == 'webvideos':
			csvfiles = glob.glob(os.path.join(self.folder, "*.xls*"))
		else:
			csvfiles = glob.glob(os.path.join(self.folder, "*.csv"))

		if arg1 == 'concat':
			return self.concat_csv(csvfiles, arg2)
		elif arg1 == 'multi':
			return self.multi_csv(csvfiles)
		elif arg1 == 'web':
			return self.web_photo(arg2, length)
		elif arg1 == 'cam':
			return self.cameras(csvfiles)
		elif arg1 == 'num_ph':
			return self.num_ph(csvfiles)
		elif arg1 == 'press':
			return self.press_csv(csvfiles)
		elif arg1 == 'multic':
			return self.concat_multi(csvfiles)
		elif arg1 == 'webvideos':
			return self.webvideos(csvfiles)

	def write_spreadsheet(self, sheet, worksheet, data, start_row):
		scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
		creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
		client = gspread.authorize(creds)

		sheet = client.open(sheet)
		worksheet = sheet.worksheet(worksheet)

		start_letter = 'A'
		end_letter = string.ascii_uppercase[len(data[0]) - 1]
		end_row = start_row + len(data) - 1
		range = "%s%d:%s%d" % (start_letter, start_row, end_letter, end_row)
		cell_list = worksheet.range(range)

		try:
			idx = 0
			for (start_row, rowlist) in enumerate(data):
				for (colnum, value) in enumerate(rowlist):
					cell_list[idx].value = value
					idx += 1
					if idx >= len(cell_list):
						break

			worksheet.update_cells(cell_list)

		except:
			print("Exception")

	def to_seconds(self, s):
		hr, minut, sec = [int(x) for x in s.split(':')]
		return hr*3600 + minut*60 + sec

	def rename(self, files):
		for fl in files:
			clean_name = ''.join(fl.split('-')[:-4])
			print(clean_name)
			final_name = clean_name.replace('-', '_')
			print(final_name)
			os.rename(fl, os.path.join(self.folder, final_name+'.xlsx'))

	def list_append(self, a_list, a_value):
		a_list.append(a_value)


	def concat_csv(self, csvfiles, arg2):
		global for_printing
		for_printing = []
		
		for csvfile in csvfiles:
			print(os.path.split(csvfile)[1])
			self.list_append(for_printing, os.path.split(csvfile)[1])
			self.dfs.append(pd.read_csv(csvfile, sep = '\t'))

		allcsv = pd.concat(self.dfs, ignore_index=True)
		print(allcsv.Brand.isnull().sum(), "empty line(s) are deleted")
		self.list_append(for_printing, str(allcsv.Brand.isnull().sum()) + ' ' +"empty line(s) are deleted")

		allcsv = allcsv[allcsv.Brand.notnull()]
		allcsv = allcsv.sort_values(by=['Sequence Frame Number'])
		allcsv['Location'] = allcsv["Location"].apply(lambda x: ''.join([" " if ord(i) < 32 or ord(i) > 126 else i for i in x]))
		print(len(allcsv), "lines are created from", len(csvfiles), "files")
		self.list_append(for_printing, str(len(allcsv)) + ' ' + "lines are created from"+ ' ' + str(len(csvfiles)) + ' ' +"files")
 
		brand = sorted(list(set(allcsv.Brand)))
		brand = [b.replace('  ', '').replace('_', '') for b in brand]
		brand = [re.sub("\d+", "", b) for b in brand]
		location = sorted(list(set(allcsv.Location)))
		location = [l.replace('  ', '').replace('_', '') for l in location]
		location = [re.sub("\d+", "", l) for l in location]

		if len(brand) > 1:
			for string in brand[:]:
				choices = process.extract(string, brand, limit=2)
				if (choices[0][1] - choices[1][1]) < 10 and (choices[0][1] - choices[1][1]) > 0:
					self.wrong_brands.append((choices[0][0], choices[1][0]))
			j = 0
			for i in list(set(self.wrong_brands)):
				j += 1
				print(i, "\t")
				self.list_append(for_printing, str(i) + ' ' +"\t")

			if len(list(set(self.wrong_brands))) == 0:
				print("No wrong brands are detected")
				self.list_append(for_printing, "No wrong brands are detected")
			else:
				print(j, "wrong brand(s) are detected!")
				self.list_append(for_printing, str(j) + ' ' + "wrong brand(s) are detected!")
		if len(location) > 1:
			for string in location[:]:
				choices = process.extract(string, location, limit=2)
				if (choices[0][1] - choices[1][1]) < 5 and (choices[0][1] - choices[1][1]) > 0:
					self.wrong_locations.append((choices[0][0], choices[1][0]))
			j = 0
			for i in list(set(self.wrong_locations)):
				j += 1
				print(i, "\t")
				self.list_append(for_printing, str(i) + ' ' +"\t")

			if len(list(set(self.wrong_locations))) == 0:
				print("No wrong touchpoints are detected", "\n")
				self.list_append(for_printing, "No wrong touchpoints are detected"+ ' ' + "\n")
			else:
				print(j, "wrong touchpoint(s) are detected!", "\n")
				self.list_append(for_printing, str(j)+ ' ' + "wrong touchpoint(s) are detected!"+ ' ' +  "\n")

		if not arg2[-4:].isdigit():
			filetime = '0000'
		else:
			filetime = ''.join(arg2.split('_')[-1:])

		hour = dt.strptime(filetime, '%H%M')
		hour = hour.strftime('%H:%M:%S')

		allcsv['Time the brand is at screen'] = self.to_seconds(hour) + allcsv['Sequence Frame Number']
		allcsv['Time the brand is at screen'] = pd.to_datetime(allcsv['Time the brand is at screen'], unit='s').dt.time

		pd.io.formats.format.header_style = None
		writer = pd.ExcelWriter(arg2+'.xlsx', engine='xlsxwriter')
		allcsv.to_excel(writer,'Sheet1', index=None)

		workbook  = writer.book
		worksheet = writer.sheets['Sheet1']

		format1 = workbook.add_format({'num_format': 'hh:mm:ss'})
		worksheet.set_column('C:C', None, format1)

		writer.save()

		return for_printing

	def multi_csv(self, csvfiles):
		for_printing = []

		for csvfile in csvfiles:
			try:
				print(os.path.split(csvfile)[1])

				self.list_append(for_printing, os.path.split(csvfile)[1])
				self.wrong_brands = []
				self.wrong_locations = []
				df = pd.read_csv(csvfile, sep = '\t', error_bad_lines=False, encoding='latin1')
				
				#create a txt file for checking differect types of brand_location
				df['brand_location'] = df['Brand'] + '_' + df['Location']
				df1 = df['brand_location'].drop_duplicates().sort_values()
				df1.to_csv('brand_location.txt', mode='a', index=False)
				with open('brand_location.txt', 'a') as f: 
					f.write(os.path.split(csvfile)[1]+'\n')
				del df['brand_location']

				print(df.Brand.isnull().sum(), "empty line(s) are deleted")
				self.list_append(for_printing, str(df.Brand.isnull().sum()) + ' ' +"empty line(s) are deleted")

				df = df[df.Brand.notnull()]
				df = df.sort_values(by=['Sequence Frame Number'])
				print(len(df), "lines are created")
				self.list_append(for_printing, str(len(df)) + ' '  + "lines are created")
				if len(df) == 0:
					print(os.path.split(csvfile), "contains no entries")
					self.list_append(for_printing, os.path.split(csvfile)[1]+ ' ' +"contains no entries")
					continue

				brand = sorted(list(set(df.Brand)))
				brand = [b.replace('  ', '').replace('_', '') for b in brand]
				brand = [re.sub("\d+", "", b) for b in brand]
				location = sorted(list(set(df.Location)))
				location = [l.replace('  ', '').replace('_', '') for l in location]
				location = [re.sub("\d+", "", l) for l in location]

				if len(brand) > 1:
					for string in brand[:]:
						choices = process.extract(string, brand, limit=2)
						if (choices[0][1] - choices[1][1]) < 10 and (choices[0][1] - choices[1][1]) > 0:
							self.wrong_brands.append((choices[0][0], choices[1][0]))
					j = 0
					for i in list(set(self.wrong_brands)):
						j += 1
						print(i, "\t")
						self.list_append(for_printing, str(i) + ' ' + "\t")

					if len(list(set(self.wrong_brands))) == 0:
						print("No wrong brands are detected")
						self.list_append(for_printing, "No wrong brands are detected")
					else:
						print(j, "wrong brand(s) are detected!")
						self.list_append(for_printing, str(j) + ' ' +  "wrong brand(s) are detected!")
				if len(location) > 1:
					for string in location[:]:
						choices = process.extract(string, location, limit=2)
						if (choices[0][1] - choices[1][1]) < 5 and (choices[0][1] - choices[1][1]) > 0:
							self.wrong_locations.append((choices[0][0], choices[1][0]))
					j = 0
					for i in list(set(self.wrong_locations)):
						j += 1
						print(i, "\t")
						self.list_append(for_printing, str(i) + ' ' + "\t")

					if len(list(set(self.wrong_locations))) == 0:
						print("No wrong touchpoints are detected", "\n")
						self.list_append(for_printing,  "No wrong touchpoints are detected"+ ' ' + "\n")
					else:
						print(j, "wrong touchpoint(s) are detected!", "\n")
						self.list_append(for_printing, str(j)+ ' ' + "wrong touchpoint(s) are detected!"+ ' ' + "\n")

				name = os.path.split(csvfile)[1]
				pattern = re.compile(r'-\w+')
				final_name = re.sub(pattern, '', name).replace('.csv', '')

				if (len(str(df['Sequence Frame Number'].values[0]))) > 5 and not (name.startswith('periph') or name.startswith('WV')):
					df['Sequence Frame Number'] = df['Sequence Frame Number'].str.replace(final_name+'_', '').astype('int')

				if not final_name[-4:].isdigit():
					filetime = '0000'
				elif len(''.join(final_name.split('_')[-1:])) > 4:
					filetime = '0000'
					#filetime = raw_input('Please give the starting time of the file '+'\n'+csvfile+'\n')
				elif int(final_name[-4:]) > 2359:
					filetime = '0000'
					#filetime = raw_input('The time is not correct! Please give the starting time of the file '+'\n'+csvfile+'\n')
				else:
					filetime = final_name[-4:]

				hour = dt.strptime(filetime, '%H%M')
				hour = hour.strftime('%H:%M:%S')

				if not (str(df['Sequence Frame Number'].values[0]).startswith('WV') or name.startswith('periph') or name.startswith('WV')):
					df['Time the brand is at screen'] = self.to_seconds(hour) + df['Sequence Frame Number']
					df['Time the brand is at screen'] = pd.to_datetime(df['Time the brand is at screen'], unit='s').dt.time
				else:
					
					df['start_time'] = df['Sequence Frame Number'].str.split('_').str[-2]
					df['seconds_to_add'] = df['Sequence Frame Number'].str.split('_').str[-1]

					df['start_time'] = pd.to_datetime(df.start_time, format='%H%M').dt.strftime('%H:%M:%S')
					
					df['Time the brand is at screen'] = df['start_time'].apply(lambda x: self.to_seconds(x)) + df['seconds_to_add'].astype(long)
					df['Time the brand is at screen'] = pd.to_datetime(df['Time the brand is at screen'], unit='s').dt.time
					del df['start_time']
					del df['seconds_to_add']

			except Exception as e:
				print("Check the file " + csvfile + "\n Probably has wrong entries" + ". Perhaps that helps:" + str(e))
				self.list_append(for_printing, "Check the file " + os.path.split(csvfile)[1] + ". Perhaps that helps:" + str(e))
					
			
			writer = pd.ExcelWriter(csvfile+".xlsx", engine='xlsxwriter')
			pd.io.formats.format.header_style = None
			df.to_excel(writer,'Sheet1', index=None)

			workbook  = writer.book
			worksheet = writer.sheets['Sheet1']

			format1 = workbook.add_format({'num_format': 'hh:mm:ss'})
			worksheet.set_column('C:C', None, format1)

			writer.save()


		print("the total files are", len(csvfiles))
		self.list_append(for_printing, "the total files are"+ ' ' + str(len(csvfiles)))

		return for_printing

	def concat_multi(self, csvfiles):
		global for_printing
		for_printing = []
		
		a_dict = {}
		# key: onoma_arxeiou value: csv ton annotator
		for csvfile in csvfiles:
			key = os.path.split(csvfile)[1].split('-')[0]
			value = csvfile
			if key not in a_dict.keys():
				a_dict[key] = []
				a_dict[key].append(value)
			else:
				a_dict[key].append(value)

		# key: onoma_arxeiou value: ta data ton csv se mia lista
		dfdict = {}

		for k, v in a_dict.items():
			if k not in dfdict.keys():
				dfdict[k] = []
				for value in v:
					dfdict[k].append(pd.read_csv(value, sep = '\t'))
			else:
				for value in v:
					dfdict[k].append(pd.read_csv(value, sep = '\t'))

		for k,v in dfdict.items():
			self.wrong_brands = []
			self.wrong_locations = []
			print(k)
			self.list_append(for_printing, k)
			allcsv = pd.concat(v, ignore_index=True)

			#create a txt file for checking differect types of brand_location
			allcsv['brand_location'] = allcsv['Brand'] + '_' + allcsv['Location']
			df1 = allcsv['brand_location'].drop_duplicates().sort_values()
			df1.to_csv('brand_location.txt', mode='a', index=False)
			with open('brand_location.txt', 'a') as f: 
				f.write(os.path.split(csvfile)[1]+'\n')
			del allcsv['brand_location']

			print(allcsv.Brand.isnull().sum(), "empty line(s) are deleted")
			self.list_append(for_printing, str(allcsv.Brand.isnull().sum()) + ' ' +"empty line(s) are deleted")

			allcsv = allcsv[allcsv.Brand.notnull()]
			# allcsv['Sequence Frame Number'] = allcsv['Sequence Frame Number'].str.replace(r'\.','')
			# allcsv['Sequence Frame Number'] = allcsv['Sequence Frame Number']
			allcsv = allcsv.sort_values(by=['Sequence Frame Number'])
			allcsv['Location'] = allcsv["Location"].apply(lambda x: ''.join([" " if ord(i) < 32 or ord(i) > 126 else i for i in x]))
			print(len(allcsv), "lines are created from", len(v), "files")
			self.list_append(for_printing, str(len(allcsv)) + ' ' + "lines are created from"+ ' ' + str(len(v)) + ' ' +"files")
	 
			brand = sorted(list(set(allcsv.Brand)))
			brand = [b.replace('  ', '').replace('_', '') for b in brand]
			brand = [re.sub("\d+", "", b) for b in brand]
			location = sorted(list(set(allcsv.Location)))
			location = [l.replace('  ', '').replace('_', '') for l in location]
			location = [re.sub("\d+", "", l) for l in location]

			if len(brand) > 1:
				for string in brand[:]:
					try:
						choices = process.extract(string, brand, limit=2)
						if (choices[0][1] - choices[1][1]) < 10 and (choices[0][1] - choices[1][1]) > 0:
							self.wrong_brands.append((choices[0][0], choices[1][0]))
					except Exception as e:
						self.list_append(for_printing, str(e) + ' ' + string  + ' ' + csvfile)
						print(e, string, csvfile)
				j = 0
				for i in list(set(self.wrong_brands)):
					j += 1
					print(i, "\t")
					self.list_append(for_printing, str(i) + ' ' +"\t")

				if len(list(set(self.wrong_brands))) == 0:
					print("No wrong brands are detected")
					self.list_append(for_printing, "No wrong brands are detected")
				else:
					print(j, "wrong brand(s) are detected!")
					self.list_append(for_printing, str(j) + ' ' + "wrong brand(s) are detected!")
			if len(location) > 1:
				try:
					for string in location[:]:
						choices = process.extract(string, location, limit=2)
						if (choices[0][1] - choices[1][1]) < 5 and (choices[0][1] - choices[1][1]) > 0:
							self.wrong_locations.append((choices[0][0], choices[1][0]))
				except Exception as e:
					self.list_append(for_printing, str(e) + ' ' + string  + ' ' + csvfile)
					print(e, string, csvfile)

				j = 0
				for i in list(set(self.wrong_locations)):
					j += 1
					print(i, "\t")
					self.list_append(for_printing, str(i) + ' ' +"\t")

				if len(list(set(self.wrong_locations))) == 0:
					print("No wrong touchpoints are detected", "\n")
					self.list_append(for_printing, "No wrong touchpoints are detected"+ ' ' + "\n")
				else:
					print(j, "wrong touchpoint(s) are detected!", "\n")
					self.list_append(for_printing, str(j)+ ' ' + "wrong touchpoint(s) are detected!"+ ' ' +  "\n")

			if not k[-4:].isdigit():
				filetime = '0000'
			elif len(''.join(k.split('_')[-1:])) > 4:
				filetime = '0000'
				#filetime = raw_input('Please give the starting time of the file '+'\n'+csvfile+'\n')
			elif int(k[-4:]) > 2359:
				filetime = '0000'
				#filetime = raw_input('The time is not correct! Please give the starting time of the file '+'\n'+csvfile+'\n')
			else:
				filetime = k[-4:]


			hour = dt.strptime(filetime, '%H%M')
			hour = hour.strftime('%H:%M:%S')

			if not (str(allcsv['Sequence Frame Number'].values[0]).startswith('WV') or k.startswith('periph') or k.startswith('WV')):
				allcsv['Time the brand is at screen'] = self.to_seconds(hour) + allcsv['Sequence Frame Number']
				allcsv['Time the brand is at screen'] = pd.to_datetime(allcsv['Time the brand is at screen'], unit='s').dt.time
			else:
				allcsv['start_time'] = allcsv['Sequence Frame Number'].str.split('_').str[-2]
				allcsv['seconds_to_add'] = allcsv['Sequence Frame Number'].str.split('_').str[-1]
				
				allcsv['start_time'] = pd.to_datetime(allcsv.start_time, format='%H%M').dt.strftime('%H:%M:%S')

				allcsv['Time the brand is at screen'] = allcsv['start_time'].apply(lambda x: self.to_seconds(x)) + allcsv['seconds_to_add'].astype(long)
				allcsv['Time the brand is at screen'] = pd.to_datetime(allcsv['Time the brand is at screen'], unit='s').dt.time
				del allcsv['start_time']
				del allcsv['seconds_to_add']

			pd.io.formats.format.header_style = None
			writer = pd.ExcelWriter(k+'.xlsx', engine='xlsxwriter')
			allcsv.to_excel(writer,'Sheet1', index=None)

			workbook  = writer.book
			worksheet = writer.sheets['Sheet1']

			format1 = workbook.add_format({'num_format': 'hh:mm:ss'})
			worksheet.set_column('C:C', None, format1)

			writer.save()

		return for_printing

	def web_photo(self, arg2, length):
		for_printing = []

		xls_images = pd.read_csv('https://docs.google.com/spreadsheets/d/' +
						   '1J7UpUMPb7tQ1Gpg9aAMOFHAXMW4OtzRcsUIzcgRaWMQ' +
						   '/export?gid=2030600446&format=csv',
						   index_col=0)
		row_toWrite = len(xls_images[xls_images.columns[0:1]].values) + 2

		print(os.path.split(arg2)[1])
		self.list_append(for_printing, os.path.split(arg2)[1])

		df = pd.read_csv(arg2, sep = '\t', error_bad_lines=False)

		file_name = re.sub(r'(\d)-(\d)', r'\1_\2', os.path.split(arg2)[1])
		pattern2 = re.compile(r'-\w+')
		newName = re.sub(pattern2, '', file_name).replace('.csv', '')
		print(newName, '----->', [time.strftime("%d/%m/%Y"), newName, len(df.PhotoURL.unique())])
		self.list_append(for_printing, newName + ' ' + '----->' + ' ' + ' '.join([time.strftime("%d/%m/%Y"), newName, str(len(df.PhotoURL.unique()))]))
		self.entries.append([time.strftime("%d/%m/%Y"), newName, len(df.PhotoURL.unique())])
		if length > 1:
			for i in range(length):
				if row_toWrite == 0:
					self.write_spreadsheet('web_images', 'clean_photos', [self.entries[-1]], 2)
					break
				else:
					self.write_spreadsheet('web_images', 'clean_photos', [self.entries[-1]], row_toWrite)
					break
		else:
			if row_toWrite == 0:
				self.write_spreadsheet('web_images', 'clean_photos', self.entries, 2)
			else:
				self.write_spreadsheet('web_images', 'clean_photos', self.entries, row_toWrite)


		print(df.Sponsor.isnull().sum(), "empty line(s) are deleted")
		self.list_append(for_printing, str(df.Sponsor.isnull().sum()) + ' '  + "empty line(s) are deleted")
		df = df[df.Sponsor.notnull()]
		df = df.sort_values(by=['ArtID'])
		df = df.rename(columns = {'Other':'Hits'})
		print(len(df), "lines are created")
		self.list_append(for_printing, str(len(df)) +  ' ' + "lines are created")

		brand = sorted(list(set(df.Sponsor)))
		brand = [b.replace('  ', '').replace('_', '') for b in brand]
		brand = [re.sub("\d+", "", b) for b in brand]
		location = sorted(list(set(df.Touchpoint)))
		location = [l.replace('  ', '').replace('_', '') for l in location]
		location = [re.sub("\d+", "", l) for l in location]

		if len(brand) > 1:
			for string in brand[:]:
				choices = process.extract(string, brand, limit=2)
				if (choices[0][1] - choices[1][1]) < 10 and (choices[0][1] - choices[1][1]) > 0:
					self.wrong_brands.append((choices[0][0], choices[1][0]))
			j = 0
			for i in list(set(self.wrong_brands)):
				j += 1
				print(i, "\t")
				self.list_append(for_printing, str(i) + ' ' +"\t")

			if len(list(set(self.wrong_brands))) == 0:
				print("No wrong brands are detected")
				self.list_append(for_printing, "No wrong brands are detected")
			else:
				print(j, "wrong brand(s) are detected!")
				self.list_append(for_printing, str(j) + ' '  + "wrong brand(s) are detected!")
		else:
			print("No wrong brands are detected")
			self.list_append(for_printing, "No wrong brands are detected")
				
		if len(location) > 1:
			for string in location[:]:
				try:
					choices = process.extract(string, location, limit=2)
					if (choices[0][1] - choices[1][1]) < 5 and (choices[0][1] - choices[1][1]) > 0:
						self.wrong_locations.append((choices[0][0], choices[1][0]))
				except:
					continue
			j = 0
			for i in list(set(self.wrong_locations)):
				j += 1
				print(i, "\t")
				self.list_append(for_printing, str(i) + ' ' +"\t")

			if len(list(set(self.wrong_locations))) == 0:
				print("No wrong touchpoints are detected", "\n")
				self.list_append(for_printing, "No wrong touchpoints are detected" + ' ' + "\n")
			else:
				print(j, "wrong touchpoint(s) are detected!", "\n")
				self.list_append(for_printing, str(j)+ ' ' + "wrong touchpoint(s) are detected!"+ ' ' + "\n")
		else:
			print("No wrong touchpoints are detected", "\n")
			self.list_append(for_printing, "No wrong touchpoints are detected" + ' ' + "\n")

		self.fname = newName.replace('zip', '')+'.xls'
		self.fname = self.fname.replace('..', '.')
		self.fname = self.fname.replace('images', 'report')
		self.fname = re.sub(r'(\d)_(\d)', r'\1-\2', self.fname)

		try:
			df1 = pd.read_excel(os.path.join(os.getcwd(),self.fname), 'Article')
			df2 = pd.read_excel(os.path.join(os.getcwd(),self.fname), 'Text')

			writer = pd.ExcelWriter(os.path.join(os.getcwd(),self.fname), engine='xlsxwriter', options={'strings_to_urls': False})
		except:
			self.fname = newName.replace('zip', '')+'.xlsx'
			self.fname = self.fname.replace('..', '.')
			self.fname = self.fname.replace('images', 'report')
			self.fname = re.sub(r'(\d)_(\d)', r'\1-\2', self.fname)
			df1 = pd.read_excel(os.path.join(os.getcwd(),self.fname), 'Article')
			df2 = pd.read_excel(os.path.join(os.getcwd(),self.fname), 'Text')

			writer = pd.ExcelWriter(os.path.join(os.getcwd(),self.fname), engine='xlsxwriter', options={'strings_to_urls': False})
		pd.io.formats.format.header_style = None

		df1.to_excel(writer, 'Article', index=None)
		df2.to_excel(writer, 'Text', index=None)
		df.to_excel(writer, 'Photo', index=None)

		writer.save()

		return for_printing

	def press_csv(self, csvfiles):
		for_printing = []

		for csvfile in csvfiles:
			press_fname = os.path.basename(csvfile).replace('.csv', '')
			print(press_fname+".xlsx")
			self.list_append(for_printing, press_fname+".xlsx")
			df = pd.read_csv(csvfile, sep = ';', error_bad_lines=False, encoding = "utf-8")
			
			print(df.Date.isnull().sum(), "empty line(s) will be deleted")
			self.list_append(for_printing, str(df.Date.isnull().sum()) + ' ' + "empty line(s) will be deleted")
			df = df[df.Date.notnull()]
			df['Date'] = df['Date'].apply(lambda x : dt.strptime(x, '%d/%m/%Y').strftime('%d/%m/%Y'))
			df = df.sort_values(by=['Newspaper'])
			print(len(df), "lines are created")
			self.list_append(for_printing, str(str(len(df)) + ' ' + "lines are created"))

			writer = pd.ExcelWriter(press_fname+".xlsx", engine='xlsxwriter', date_format='dd\/mm\/yyyy')
			pd.io.formats.format.header_style = None
			df.to_excel(writer,'Sheet1', index=None)

			workbook  = writer.book
			
			header_fmt = workbook.add_format({'bold': True})
			worksheet = writer.sheets['Sheet1']
			worksheet.set_row(0, None, header_fmt)
			worksheet.freeze_panes(1,0)

			writer.save()

		print("the total files are", len(csvfiles))
		self.list_append(for_printing, "the total files are"+ ' ' + str(len(csvfiles)))

		return for_printing

	def cameras(self, csvfiles):
		for csvfile in csvfiles:
			print(os.path.split(csvfile)[1])
			df = pd.read_csv(csvfile, sep = '\t', error_bad_lines=False, encoding='latin1')

			print(df.Brand.isnull().sum(), "empty line(s) are deleted")
			df = df[df.Brand.notnull()]

			df1 = df[df['Location'].str.contains('whatever')]
			df2 = df[df['Location'].str.contains('whatever') == False]

			df1 = df1[['Brand', 'Time the brand is at screen', 'Duration', 'Sequence Frame Number']]
			df1 = df1.rename(columns={'Brand': 'Non-commercial asset', 'Time the brand is at screen': 'Time Non-commercial asset is at screen'})
			print(len(df1), "lines are created for _noncommercial")

			pd.options.mode.chained_assignment = None
			df2['Sunny/No Sunny'] = np.where(df2['Location'].str.contains('No Sunny'), int('0'), int('1'))
			df2['Location'] = df2['Location'].str.replace(' - Sunny', '')
			df2['Location'] = df2['Location'].str.replace(' - No Sunny', '')
			df2['Location'] = df2['Location'].str.replace(' Akuro', '')
			df2 = df2[['Brand', 'Location', 'Time the brand is at screen', 'Duration', 'Sunny/No Sunny', 'Sequence Frame Number']]
			df2 = df2.rename(columns={'Brand': 'Camera', 'Location': 'Segment', 'Time the brand is at screen': 'Camera is at screen' })
			print(len(df2), "lines are created for _camerasAngles")

			#noncommercial
			writer = pd.ExcelWriter(csvfile+"_noncommercial.xlsx", engine='xlsxwriter')
			pd.io.formats.format.header_style = None
			df1.to_excel(writer,'Sheet1', index=None)

			workbook  = writer.book
			worksheet = writer.sheets['Sheet1']

			format1 = workbook.add_format({'num_format': 'hh:mm:ss'})
			worksheet.set_column('B:B', None, format1)

			#camerasAngles
			writer = pd.ExcelWriter(csvfile+"_camerasAngles.xlsx", engine='xlsxwriter')
			pd.io.formats.format.header_style = None
			df2.to_excel(writer,'Sheet1', index=None)

			workbook  = writer.book
			worksheet = writer.sheets['Sheet1']

			format1 = workbook.add_format({'num_format': 'hh:mm:ss'})
			worksheet.set_column('C:C', None, format1)

	def num_ph(self, csvfiles):
		xls_images = pd.read_csv('https://docs.google.com/spreadsheets/d/' +
						   '1J7UpUMPb7tQ1Gpg9aAMOFHAXMW4OtzRcsUIzcgRaWMQ' +
						   '/export?gid=2030600446&format=csv',
						   index_col=0)
		row_toWrite = len(xls_images[xls_images.columns[0:1]].values) + 2

		for csvfile in csvfiles:
			df = pd.read_csv(csvfile, sep = '\t', error_bad_lines=False)
			file_name = re.sub(r'(\d)-(\d)', r'\1_\2', os.path.split(csvfile)[1])
			pattern2 = re.compile(r'-\w+')
			newName = re.sub(pattern2, '', file_name).replace('.csv', '')
			print(newName, '----->', [time.strftime("%d/%m/%Y"), newName, len(df.PhotoURL.unique())])
			entries.append([time.strftime("%d/%m/%Y"), newName, len(df.PhotoURL.unique())])
			if row_toWrite == 0:
				write_spreadsheet('web_images', 'clean_photos', entries, 2)
			else:
				write_spreadsheet('web_images', 'clean_photos', entries, row_toWrite)

	def finalize(self):
		for infile in glob.glob(os.path.join(self.folder, '*.*')):
			if 'xlsx' in infile:
				continue
			else:
				os.remove(infile)
			
		self.rename(glob.glob(os.path.join(self.folder, '*.xlsx')))

	def finalreport(self, fname):
		for_printing = []

		name, ext = os.path.splitext(fname)
		xlsx = ExcelFile(fname)
		rxlsx = name + '_finalreport' + '.xlsx'

		if ext == '.xlsx':
			writer = ExcelWriter(rxlsx, engine='xlsxwriter', options={'strings_to_urls': False})
		elif ext == '.xls':
			writer = ExcelWriter(rxlsx, engine='xlsxwriter', options={'strings_to_urls': False})
		else:
			print('wrong file')
			self.list_append(for_printing,  'wrong file')

		art_tab = xlsx.parse(xlsx.sheet_names[0])
		#print(art_tab.to_dict())
		text_tab = xlsx.parse(xlsx.sheet_names[1])
		photo_tab = xlsx.parse(xlsx.sheet_names[2])

		tp1_tab = concat([text_tab,photo_tab], join='outer', sort=False)
		try:
			tp2_tab = merge(art_tab,tp1_tab, how='outer', on='ArtID', sort=False)
		except:
			art_tab['ArtID'] = art_tab['ArtID'].astype(int)
			tp1_tab['ArtID'] = tp1_tab['ArtID'].astype(int)
			tp2_tab = merge(art_tab,tp1_tab, on='ArtID', sort=False)
		#remove unwanted columns from final excel depending on project
		tp2_tab = tp2_tab.drop(['PhotoID', 'TextID', 'Hits'], axis=1)
		tp2_tab = tp2_tab[['ArtID', 'URL', 'PhotoURL', 'Date', 'WC', 'Keyword', 'Mention', 'Sponsor', 'Touchpoint', 'Percentage']]
		tp2_tab = tp2_tab.dropna(subset=['Keyword', 'Mention', 'Sponsor', 'Touchpoint'], how='all')
		tp2_tab.Sponsor.fillna(tp2_tab.Mention, inplace=True)
		tp2_tab.Touchpoint.fillna('Text', inplace=True)
		del tp2_tab['Keyword']
		del tp2_tab['Mention']
		tp2_tab.reset_index()
		tp2_tab['ArtID'] = range(1, len(tp2_tab) + 1)

		#df.columns = 'File heat Observations'.split()
		#tp1_tab.to_excel(writer,'Sheet1')
		tp2_tab.to_excel(writer, 'Sheet1', index=False)

		workbook  = writer.book
		worksheet = writer.sheets['Sheet1']
		worksheet.freeze_panes(1,0)
		writer.close()

		print(rxlsx+' is ready!')
		self.list_append(for_printing,  rxlsx+' is ready!')

		return ''.join(for_printing)

	def webvideos(self, csvfiles):

		for_printing = []

		for csvfile in csvfiles:
			print(csvfile)
			name, ext = os.path.splitext(csvfile)
	
			xlsx = ExcelFile(csvfile)
			rxlsx = name + '_finalreport' + '.xlsx'

			if ext == '.xlsx':
				writer = ExcelWriter(rxlsx, engine='xlsxwriter', options={'strings_to_urls': False})
			elif ext == '.xls':
				writer = ExcelWriter(rxlsx, engine='xlsxwriter', options={'strings_to_urls': False})
			else:
				print('wrong file')
				self.list_append(for_printing,  'wrong file')

			print(xlsx.sheet_names)
			if len(xlsx.sheet_names) <= 3:
				inArticles_tab = xlsx.parse(xlsx.sheet_names[0])
				#inArticles_tab['date'] = inArticles_tab['date'].apply(lambda x : dt.strptime(x, '%d/%m/%Y').strftime('%d/%m/%Y'))

				youtube_tab = xlsx.parse(xlsx.sheet_names[1])
				youtube_tab['date'] = youtube_tab['date'].dt.strftime('%d/%m/%Y')

				anno_tab = xlsx.parse(xlsx.sheet_names[2])
				tp1_tab = concat([inArticles_tab, videoSites_tab], join='outer')
			elif len(xlsx.sheet_names) == 4:
				inArticles_tab = xlsx.parse(xlsx.sheet_names[0])
				#inArticles_tab['date'] = inArticles_tab['date'].apply(lambda x : dt.strptime(x, '%d/%m/%Y').strftime('%d/%m/%Y'))
				
				videoSites_tab = xlsx.parse(xlsx.sheet_names[1])
				videoSites_tab['date'] = pd.to_datetime(videoSites_tab['date'])
				videoSites_tab['date'] = videoSites_tab['date'].dt.strftime('%d/%m/%Y')

				youtube_tab = xlsx.parse(xlsx.sheet_names[2])
				#youtube_tab['date'] = youtube_tab['date'].dt.strftime('%d/%m/%Y')

				anno_tab = xlsx.parse(xlsx.sheet_names[3])
				tp1_tab = concat([inArticles_tab, videoSites_tab, youtube_tab], join='outer')
			else:
				print("wrong tab number")
				self.list_append(for_printing,  "wrong tab number")

			dfs = []

			headers = list(anno_tab.columns.values)
			del headers[:2]
			totalheaders = len(headers)

			for header in headers:
				header = header.encode('ascii', 'replace')
				#header = re.sub('[^A-z0-9@# ]', '', header)
				anno_tab.loc[anno_tab[str(header)] == 1, str(header)] = str(header)
				df1 = str(header).replace(' ', '') + '_tab'
				tp2_tab = merge(anno_tab, tp1_tab, how='outer', on='url', sort=True)
				df1 = tp2_tab[['title', 'url', 'date', 'user', 'duration', 'views', str(header)]]
				df1.rename(columns={str(header):'sponsor'}, inplace=True)
				dfs.append(df1)


			tpfin_tab = concat(dfs, join='outer')
	
			tpfin_tab = tpfin_tab[['title', 'url', 'date', 'user', 'duration', 'views', 'sponsor']]
			tpfin_tab = tpfin_tab[tpfin_tab['sponsor'].notnull()]
			tpfin_tab = tpfin_tab[tpfin_tab['sponsor'] != 0]
			tpfin_tab.user.fillna('n/a', inplace=True)

			tpfin_tab.reset_index()
			tpfin_tab['ArtID'] = range(1, len(tpfin_tab) + 1)

			#regex_pat = re.compile(r'\.\d')
			tpfin_tab['sponsor'] = tpfin_tab['sponsor'].str.replace(r'\.\d+', r'')

			# tpfin_tab['sponsor'] = tpfin_tab['sponsor'].str.replace(regex_pat, '', regex=True)
			
			tpfin_tab = tpfin_tab[['ArtID', 'title', 'url', 'date', 'user', 'duration', 'views', 'sponsor']]
			tpfin_tab['sponsor'] = tpfin_tab['sponsor']
			tpfin_tab.to_excel(writer, 'Sheet1', index=False)

			workbook  = writer.book
			worksheet = writer.sheets['Sheet1']
			worksheet.freeze_panes(1,0)

			format1 = workbook.add_format({'num_format': 'dd/mm/yyyy'})
			format2 = workbook.add_format({'num_format': 'hh:mm:ss'})
			worksheet.set_column('D:D', None, format1)
			worksheet.set_column('F:F', None, format2)

			writer.save()

			print(rxlsx+' is ready!')
			self.list_append(for_printing,  os.path.split(rxlsx)[1]+' is ready!')

		return for_printing	




