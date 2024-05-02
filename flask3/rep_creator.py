#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gspread
import zipfile
import time
import string
import os
import sys
import re
import glob
import csv
import xlrd
import xlwt
import xlsxwriter
import itertools
import pandas as pd
from pandas import *
from oauth2client.service_account import ServiceAccountCredentials
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import math

# reload(sys)  
# sys.setdefaultencoding('utf8')

class Report_creator():
	def __init__(self):
		self.zipfile_path = ''
		self.destination = ''
		self.entries = []
		self.dfs = []
		self.ids = []
		self.wrong_brands = []
		self.wrong_locations = []
		self.kwds = {}

	def write_spreadsheet(self, sheet, worksheet, data, start_row):
		scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
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

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			print(str(exc_tb.tb_lineno) + ' | ' + str(e))

	def unzip(self, zipfile):
		zip_ref = zipfile.ZipFile(zipfile_path, 'r')
		zip_ref.extractall(destination)
		zip_ref.close()

	def concat_csv(self, csvfiles):
		for csvfile in csvfiles:
			print(os.path.split(csvfile)[1])
			self.dfs.append(pd.read_csv(csvfile, sep = '\t'))

		allcsv = pd.concat(self.dfs, ignore_index=True)
		allcsv.to_csv(destination+'.csv', sep='\t', encoding='utf-8', index=False)

	def csv_to_xls(self, csv_file, sheet):
	#copy csv files to xlsx tabs
		with open(csv_file, "r") as fread:
			#dialect = csv.Sniffer().sniff(fread.readline(), [',',';','\t'])
			#reader = csv.reader(fread, dialect)
			print(photo_csv, csv_file)
			if photo_csv in csv_file:
				start_col = 0
				reader = csv.reader(fread, delimiter='\t', quotechar='"')
			else:
				start_col = 1
				reader = csv.reader(fread, delimiter=',', quotechar='"')
			for r, row in enumerate(reader, start=start_col):
				for c, col in enumerate(row):
					try:
						#sheet.write(r, c, str(col.encode('utf-8').strip()))
						sheet.write(r, c, str(col.strip()))
					except Exception as e:
						col = re.sub('[^A-z0-9 ]', '', str(col))
						sheet.write(r, c, col.strip()) 						
						exc_type, exc_obj, exc_tb = sys.exc_info()
						print(str(exc_tb.tb_lineno) + ' | ' + str(e))
						#continue

	def final_name(self, name_init):
		name = re.sub('[^0-9]', '', str(name_init))
		name = name[4:].replace(name[0:4], '_')
		final_name = name_init[0:4]+name+'.xlsx'
		# if final_name[4:6] == final_name[9:11] and final_name[9:11] != final_name[11:13]:
		# 	new_name = final_name.replace(final_name[9:11], '')
		# 	return new_name[0:4]+final_name[4:6]+new_name[4:]
		# else:
		return final_name

	def list_append(self, a_list, a_value):
		a_list.append(a_value)

	def creator(self, arg0, arg1, arg3, arg4=None):
		global for_printing
		global art_csv
		global photo_csv
		global results
		global zipfile_path
		global destination
		global dfs
		for_printing = []
		art_csv = arg0
		photo_csv = arg1
		results = self.final_name(art_csv)
		xls_images = pd.read_csv('https://docs.google.com/spreadsheets/d/' + 
							   '1J7UpUMPb7tQ1Gpg9aAMOFHAXMW4OtzRcsUIzcgRaWMQ' +
							   '/export?gid=2030600446&format=csv',
							   index_col=0)

		row_toWrite = len(xls_images[xls_images.columns[0:1]].values) + 2

		if arg1 == 'no':
			zipfile_path = os.path.join(arg4)
			destination = arg4.replace('.zip','')
			os.mkdir(destination)
			self.unzip(zipfile)
			csvfiles = glob.glob(os.path.join(destination, "*.*"))
			for csvfile1 in csvfiles:
				df = pd.read_csv(csvfile1, sep = '\t', error_bad_lines=False)
				file_name = re.sub(r'(\d)-(\d)', r'\1_\2', os.path.split(csvfile1)[1])
				pattern2 = re.compile(r'-\w+')
				newName = re.sub(pattern2, '', file_name).replace('.csv', '')
				print(newName, '----->', [time.strftime("%d/%m/%Y"), newName, len(df.PhotoURL.unique())])
				self.list_append(for_printing,' '.join([time.strftime("%d/%m/%Y"), newName, str(len(df.PhotoURL.unique()))]))
				self.entries.append([time.strftime("%d/%m/%Y"), newName, len(df.PhotoURL.unique())])
				if row_toWrite == 0:
					self.write_spreadsheet('web_images', 'clean_photos', self.entries, 2)
				else:
					self.write_spreadsheet('web_images', 'clean_photos', self.entries, row_toWrite)

			self.concat_csv(csvfiles)
			photo_csv = os.path.join(destination+'.csv')
		else:
			df = pd.read_csv(photo_csv, sep = '\t', error_bad_lines=False)
			file_name = re.sub(r'(\d)-(\d)', r'\1_\2', photo_csv)
			pattern2 = re.compile(r'-\w+')
			newName = re.sub(pattern2, '', file_name).replace('.csv', '')
			if len(df.PhotoURL) != 0:
				print(newName, '----->', [time.strftime("%d/%m/%Y"), newName, len(df.PhotoURL.unique())])
				self.list_append(for_printing,' '.join([time.strftime("%d/%m/%Y"), newName, str(len(df.PhotoURL.unique()))]))
				self.entries.append([time.strftime("%d/%m/%Y"), newName, len(df.PhotoURL.unique())])
				if row_toWrite == 0:
					self.write_spreadsheet('web_images', 'clean_photos', self.entries, 2)
				else:
					self.write_spreadsheet('web_images', 'clean_photos', self.entries, row_toWrite)

		#copy ids from photo_annotation
		with open(photo_csv, "r") as fread:
			dialect = csv.Sniffer().sniff(fread.readline(), [',',';','\t'])
			fread.seek(0)
			photo_reader = csv.reader(fread, dialect)
			for row in photo_reader: 
				if row[3] in (None, ""):
					print("This line ", row, " has an empty cell")
					self.list_append(for_printing, "This line " + ' '+str(row)+ ' '+ " has an empty cell")
				try:
					self.ids.append(row[0])
				except ValueError as e:
					exc_type, exc_obj, exc_tb = sys.exc_info()
					print(str(exc_tb.tb_lineno) + ' | ' + str(e))

		#copy ids from text_tab
		with open("text_tab.csv", "r") as fread:
			dialect = csv.Sniffer().sniff(fread.readline(), [',',';','\t'])
			fread.seek(0)
			text_reader = csv.reader(fread, dialect)
			for row in text_reader:
				try:
					if "twitter" in art_csv:
						if row[3] != "photo":
							#self.ids.append(int(row[0]))
							self.ids.append(row[0])
					else:
						if row[3] != "photo":
							#self.ids.append(int(row[0]))
							self.ids.append(row[0])
				except ValueError as e:
					exc_type, exc_obj, exc_tb = sys.exc_info()
					print(str(exc_tb.tb_lineno) + ' | ' + str(e))

		#all uniques ids in a list
		final_ids = list(set(self.ids))
		final_ids.sort()
		print("There are ", len(final_ids), " uniques ids from ", len(self.ids))
		self.list_append(for_printing, "There are "+ ' '  + str(len(final_ids))+ ' '  +" uniques ids from "+ ' '  +str(len(self.ids)))

		#copy unique ids in txt file
		with open("text.txt", "w") as f:
			for i in final_ids:
				#print(i)
				f.write(str(i).replace('.0','')+"\n")

		unique_ids = open("text.txt",'r').read().split('\n')

		#compare unique ids with art_tab, create art.csv
		with open('art.csv', 'w', newline='') as fwrite, open(art_csv,'r', newline='') as fread:

			if arg3 == "comma":
				#art_reader = csv.reader(fread, delimiter=',', quotechar='"')
				art_reader = csv.reader( (line.replace('\0','') for line in fread) , delimiter=',',quotechar = '"')
			else:
				art_reader = csv.reader( (line.replace('\0','') for line in fread) , delimiter=';',quotechar = '"')
				#art_reader = csv.reader(fread, delimiter=';', quotechar='"')
				
			writer = csv.writer(fwrite)
			try:
				for row in art_reader:
					col_id = row[0]
					if col_id.strip() != 'ArtID' and col_id.strip() in unique_ids:
						writer.writerow(row)
					else:
						continue
			except csv.Error as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				print(str(exc_tb.tb_lineno, row) + ' | ' + str(e))
				#sys.exit('file %s, line %d: %s' % (art_reader.line_num, e))

		#compare unique ids with text_tab, create text.csv
		with open('text.csv', 'w', newline='') as fwrite, open("text_tab.csv", 'r', newline='') as fread:

			text_reader = csv.reader(fread, delimiter=',', quotechar='"')

			writer = csv.writer(fwrite)
			try:
				for row in text_reader:
					col_id = row[0]
					if col_id.strip() != 'ArtID' and col_id.strip() in unique_ids:
						writer.writerow(row)
					else:
						continue
			except csv.Error as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				print(str(exc_tb.tb_lineno) + ' | ' + str(e))
				sys.exit('file %s, line %d: %s' % (text_reader.line_num, e))

		#create xlsx file with 3 tabs
		wb = xlsxwriter.Workbook(results, {'strings_to_urls': False, 'num_format': '0'})

		sh1 = wb.add_worksheet("Article")
		if "twitter" in art_csv:
			sh1.write("A1","ArtID")
			sh1.write("B1","User")
			sh1.write("C1","URL")
			sh1.write("D1","Date")
			sh1.write("E1","Followers")
			sh1.write("F1","Text")
			sh1.write("G1","Photourl")

		elif "fb" in art_csv or "facebook" in art_csv:
			sh1.write("A1","ArtID")
			sh1.write("B1","User")
			sh1.write("C1","URL")
			sh1.write("D1","Date")
			sh1.write("E1","Friends")
			sh1.write("F1","Text")
		else:
			sh1.write("A1","ArtID")
			sh1.write("B1","User")
			sh1.write("C1","URL")
			sh1.write("D1","Date")
			sh1.write("E1","Followers")
			sh1.write("F1","Text")
			sh1.write("G1","Photourl")

		sh2 = wb.add_worksheet("Text")
		if "twitter" in art_csv:
			sh2.write("A1","ArtID")
			sh2.write("B1","TextID")
			#sh2.write("C1","User")
			#sh2.write("D1","Followers")
			sh2.write("C1","Mention")
			sh2.write("D1","Keyword")
		else:
			sh2.write("A1","ArtID")
			sh2.write("B1","TextID")
			sh2.write("C1","Mention")
			sh2.write("D1","Keyword")

		sh3 = wb.add_worksheet("Photo")
		'''
		sh3.write("A1","ArtID")
		sh3.write("B1","PhotoID")
		sh3.write("C1","PhotoURL")
		sh3.write("D1","Sponsor")
		sh3.write("E1","Touchpoint")
		sh3.write("F1","Percentage")
		sh3.write("G1","Hits")
		'''

		# copy the 3 tabs in the xlsx file
		self.csv_to_xls("art.csv", sh1)
		self.csv_to_xls("text.csv", sh2)
		self.csv_to_xls(photo_csv, sh3)

		if "twitter" in art_csv:
			sh2.set_column('G:G', None, None, {'hidden': True})
		else:
			sh2.set_column('E:E', None, None, {'hidden': True})

		wb.close()

		#delete all csv files in folder
		for infile in glob.glob(os.path.join('*.csv')):
			os.remove(infile)

		#check for empty lines in Photo
		df = pd.read_excel(os.path.join(os.getcwd(), results), 'Photo')
		print(df['Sponsor'].isnull().sum(), "empty line(s) are deleted")
		self.list_append(for_printing, str(df.Sponsor.isnull().sum()) + ' '+ "empty line(s) are deleted")
		df = df[df['Sponsor'].notnull()]
		print(len(df), "lines are created")
		self.list_append(for_printing, str(len(df)) + ' '+ "lines are created")
		df = df.rename(columns = {'Other':'Hits'})

		brand = sorted(list(set(df.Sponsor)))
		brand = [b.replace('  ', '').replace('_', '') for b in brand]
		brand = [re.sub("\d+", "", b) for b in brand]
		location = sorted(list(set(df.Touchpoint)))
		location = [l.replace('  ', '').replace('_', '') for l in location]
		location = [re.sub("\d+", "", l) for l in location]

		if len(brand) > 1 and len(location) > 1:
			for string in brand[:]:
				choices = process.extract(string, brand, limit=2)
				if (choices[0][1] - choices[1][1]) < 5 and (choices[0][1] - choices[1][1]) > 0:
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

		if len(brand) > 1 and len(location) > 1:
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
				self.list_append(for_printing, str(j)+ ' ' + "wrong touchpoint(s) are detected!"+ ' ' + "\n")

		df1 = pd.read_excel(os.path.join(os.getcwd(),results), 'Article')

		df2 = pd.read_excel(os.path.join(os.getcwd(),results), 'Text')
		df2 = df2.rename(columns = {'Unnamed: 4':''})

		pd.io.formats.format.header_style = None
		writer = pd.ExcelWriter(os.path.join(os.getcwd(),results), engine='xlsxwriter', options={'strings_to_urls': False})

		df1.to_excel(writer, 'Article', index=None)
		df2.to_excel(writer, 'Text', index=None)
		df.to_excel(writer, 'Photo', index=None)

		writer.save()

		return for_printing

	def finalreport(self):
		global rxlsx
		global for_printing
		for_printing = []
		project = art_csv.split('_')[5].split('.')[0]
		project = re.sub( r"([A-Z])", r" \1", project).split()[0]
		
		name, ext = os.path.splitext(results)
		xlsx = ExcelFile(results)
		rxlsx = name + '_finalreport' + '.xlsx'

		if ext == '.xlsx':
			writer = ExcelWriter(rxlsx, engine='xlsxwriter', options={'strings_to_urls': False})
		elif ext == '.xls':
			writer = ExcelWriter(rxlsx, engine='xlsxwriter', options={'strings_to_urls': False})
		else:
			print('wrong file')

		if project == 'twitter':
			print('Project: ' + project + ' | File: ' + results + ' | Extension: ' + ext + ' | final report: ' + rxlsx)
			self.list_append(for_printing, 'Project: ' + project + ' | File: ' + results + ' | Extension: ' + ext + ' | final report: ' + rxlsx)
			art_tab = xlsx.parse(xlsx.sheet_names[0])
			text_tab = xlsx.parse(xlsx.sheet_names[1])
			photo_tab = xlsx.parse(xlsx.sheet_names[2])

			tp1_tab = concat([text_tab, photo_tab], join='outer', sort=False)
			try:
				tp2_tab = merge(art_tab, tp1_tab, how='outer', on='ArtID', sort=False)
			except:
				art_tab['ArtID'] = art_tab['ArtID'].astype(int)
				tp1_tab['ArtID'] = tp1_tab['ArtID'].astype(int)
				tp2_tab = merge(art_tab,tp1_tab, on='ArtID', sort=False)
			#remove unwanted columns from final excel depending on project
			#tp2_tab[['User', 'Followers']].fillna(method='ffill', inplace=True)
			for col in ['User']:
				tp2_tab[col] = tp2_tab[col].ffill()
			for col in ['Followers']:
				tp2_tab[col] = tp2_tab[col].ffill()
			tp2_tab = tp2_tab[['ArtID', 'URL', 'Photourl', 'Date', 'User', 'Text', 'Followers', 'Keyword', 'Mention', 'Sponsor', 'Touchpoint', 'Percentage']]
			tp2_tab['Sponsor'].fillna(tp2_tab.Mention, inplace=True)
			tp2_tab.Touchpoint.fillna('Text', inplace=True)
			#tp2_tab = tp2_tab.drop(['PhotoURL', 'Keyword', 'Mention'], axis=1)
			del tp2_tab['Keyword']
			del tp2_tab['Mention']
			#tp1_tab.to_excel(writer,'Sheet1')
			tp2_tab = tp2_tab[tp2_tab.Sponsor != "photo"]
			tp2_tab.reset_index()
			tp2_tab['ArtID'] = range(1, len(tp2_tab) + 1)
			tp2_tab.to_excel(writer, 'Sheet1', index=False)
			#if tp2_tab['URL'].isnull().sum() != 0:
			#	try:
			#		raise Exception('null in URL column')
			#	except Exception:
			#		print 'null in URL column'
			#		sys.exit()
			
			workbook  = writer.book
			worksheet = writer.sheets['Sheet1']
			worksheet.freeze_panes(1,0)
			writer.close()
			
		elif project == 'instagram':
			print('Project: ' + project + ' | File: ' + results + ' | Extension: ' + ext + ' | final report: ' + rxlsx)
			self.list_append(for_printing, 'Project: ' + project + ' | File: ' + results + ' | Extension: ' + ext + ' | final report: ' + rxlsx)
			art_tab = xlsx.parse(xlsx.sheet_names[0])
			#print(art_tab.to_dict())
			text_tab = xlsx.parse(xlsx.sheet_names[1])
			photo_tab = xlsx.parse(xlsx.sheet_names[2])

			tp1_tab = concat([text_tab, photo_tab], join='outer')
			tp2_tab = merge(art_tab, tp1_tab, how='outer', on='ArtID', sort=True)
			for col in ['User']:
				tp2_tab[col] = tp2_tab[col].ffill()
			for col in ['URL']:
				tp2_tab[col] = tp2_tab[col].ffill()
			for col in ['Date']:
				tp2_tab[col] = tp2_tab[col].ffill()
			for col in ['Followers']:
				tp2_tab[col] = tp2_tab[col].ffill()
			for col in ['Text']:
				tp2_tab[col] = tp2_tab[col].ffill()
			for col in ['Photourl']:
				tp2_tab[col] = tp2_tab[col].ffill()
			#remove unwanted columns from final excel depending on project
			tp2_tab = tp2_tab[['ArtID', 'URL', 'Photourl', 'Date', 'User', 'Text', 'Followers', 'Keyword', 'Mention', 'Sponsor', 'Touchpoint', 'Percentage']]
			tp2_tab.Sponsor.fillna(tp2_tab.Mention, inplace=True)
			tp2_tab.Touchpoint.fillna('Text', inplace=True)
			del tp2_tab['Keyword']
			del tp2_tab['Mention']
			#tp1_tab.to_excel(writer,'Sheet1')
			tp2_tab = tp2_tab[tp2_tab.Sponsor != "photo"]
			tp2_tab.reset_index()
			tp2_tab['ArtID'] = range(1, len(tp2_tab) + 1)
			if tp2_tab['URL'].isnull().sum() != 0:
				try:
					raise Exception('null in URL column')

				except Exception as e:
					exc_type, exc_obj, exc_tb = sys.exc_info()
					print(str(exc_tb.tb_lineno) + ' | ' + str(e))
					sys.exit()

			tp2_tab.to_excel(writer, 'Sheet1', index=False)

			workbook  = writer.book
			worksheet = writer.sheets['Sheet1']
			worksheet.freeze_panes(1,0)
			writer.close()

		elif project == 'facebook':
			print('Project: ' + project + ' | Photo File: ' + results + ' | Extension: ' + ext + ' | final report: ' + rxlsx)
			self.list_append(for_printing, 'Project: ' + project + ' | Photo File: ' + results + ' | Extension: ' + ext + ' | final report: ' + rxlsx)
			art_tab = xlsx.parse(xlsx.sheet_names[0])
			text_tab = xlsx.parse(xlsx.sheet_names[1])
			photo_tab = xlsx.parse(xlsx.sheet_names[2])

			tp1_tab = concat([text_tab, photo_tab], join='outer')
			tp2_tab = merge(art_tab, tp1_tab, how='outer', on='ArtID', sort=True)

			tp2_tab = tp2_tab[['ArtID', 'URL', 'PhotoURL', 'Date', 'User', 'Text', 'Friends', 'Keyword', 'Mention', 'Sponsor', 'Touchpoint', 'Percentage']]
			tp2_tab.Sponsor.fillna(tp2_tab.Mention, inplace=True)
			tp2_tab.Touchpoint.fillna('Text', inplace=True)

			del tp2_tab['Keyword']
			del tp2_tab['Mention']

			tp2_tab = tp2_tab[tp2_tab.Sponsor != "photo"]
			tp2_tab.reset_index()
			tp2_tab['ArtID'] = range(1, len(tp2_tab) + 1)
			#if tp3_tab['URL'].isnull().sum() != 0:
			#	try:
			#		raise Exception('null in URL column')
			#	except Exception:
			#		print('null in URL column')
			#		sys.exit()
			tp2_tab.to_excel(writer, 'Sheet1', index=False)

			workbook  = writer.book
			worksheet = writer.sheets['Sheet1']
			worksheet.freeze_panes(1,0)
			writer.close()
		else:
			print('Select a valid project')
			print('Usage:')
			print('python excel_report.py twitter report.xls(x)')
			print('python excel_report.py instagram report.xls(x)')
			print('python excel_report.py facebook report_Photos.xls(x) report_Text.xls(x)')

		return ''.join(for_printing)
	

	def ontology_search(self, ontology, cell):

		for item in ontology:
			item = item.split('<=')
			official = item[0].strip()
			self.kwds[official] = []
			alt = item[1].strip()
			alist = alt.split('|')
			for a in alist:
				a = a.strip()
				self.kwds[official].append(a.lower())
		found = False
		word = ''
		for key, value in self.kwds.items():
			for alt in value:
				if alt in cell.value.lower():
					found = True
					word = key
		return found, word

	def creator_nascar(self, ont=None):
		global for_printing
		for_printing = []
		self.excel = rxlsx
		ontology = open(ont, 'r').readlines()
		entries_changed = 0
		row_number7 = 0
		row_number8 = 0

		book = xlrd.open_workbook(self.excel)
		xls = book.sheet_by_index(0)

		#wb = xlwt.Workbook()
		#newxls = wb.add_sheet("Sheet1", cell_overwrite_ok=True)
		wb = xlsxwriter.Workbook("results.xlsx")
		newxls = wb.add_worksheet("Sheet1")
		newxls.write("A1","new_Sponsor")
		newxls.write("B1","new_Touchpoint")

		cell_text = xls.col_slice(colx=5, start_rowx=1)
		cells7 = xls.col_slice(colx=7, start_rowx=1)
		cells8 = xls.col_slice(colx=8, start_rowx=1)

		if 'Abbott' in art_csv:
			for a, b, c in itertools.izip(cell_text, cells7, cells8):
				found, word = self.ontology_search(ontology, a)
				if found == True:
					entries_changed += 1
					row_number7 += 1
					if 'WMM' in b.value or 'Logo' in b.value:
						newxls.write(row_number7, 0, b.value)
						newxls.write(row_number7, 1, c.value)
					else:
						newxls.write(row_number7, 0, word)
						newxls.write(row_number7, 1, "Text - " + b.value)
				else:
					row_number7 += 1
					if 'WMM' in b.value or 'Logo' in b.value:
						newxls.write(row_number7, 0, b.value)
						newxls.write(row_number7, 1, c.value)
					else:
						newxls.write(row_number7, 0, 'Abbott')
						newxls.write(row_number7, 1, "Text - " + b.value)
		else:
			for cell7 in cells7:
				found, word = self.ontology_search(ontology, cell7)
				if found == True:
					entries_changed += 1
					row_number7 += 1
					newxls.write(row_number7, 0, word)
					newxls.write(row_number7, 1, "Text - "+cell7.value)
				else:
					row_number7 += 1
					newxls.write(row_number7, 0, cell7.value)
					newxls.write(row_number7, 1, "Text")

			for cell8 in cells8:
				row_number8 += 1
				if "Text" not in cell8.value:
					newxls.write(row_number8, 1, cell8.value)
					#newxls.write_merge(0, 0, 0, 1, "")

		print(entries_changed ,"entries have been changed!")
		self.list_append(for_printing, str(entries_changed) + ' ' +"entries have been changed!")

		wb.close()

		df_report = pd.read_excel(self.excel)
		df_results = pd.read_excel('results.xlsx')

		df = pd.concat([df_report, df_results[df_results.columns[0:2]]], axis=1)

		columns = ['Sponsor', 'Touchpoint']
		#if 'Mention' in list(df.columns.values):
		#	columns = ['Mention', 'Sponsor', 'Touchpoint']
		df.drop(columns, inplace=True, axis=1)
		df = df.rename(columns={'new_Sponsor': 'Sponsor', 'new_Touchpoint': 'Touchpoint'})

		if 'Friends' in list(df.columns.values):
			df = df[['ArtID','URL','PhotoURL','Date','User', 'Text', 'Friends','Sponsor','Touchpoint','Percentage']]
		elif 'Photourl' in list(df.columns.values):
			df = df[['ArtID','URL','Photourl','Date','User','Text','Followers','Sponsor','Touchpoint','Percentage']]
		else:
			df = df[['ArtID','URL','PhotoURL','Date','User','Text','Followers','Sponsor','Touchpoint','Percentage']]
		df.head()

		writer = pd.ExcelWriter(self.excel, engine='xlsxwriter', options={'strings_to_urls': False})
		df.to_excel(writer, 'Sheet1', index=False)

		workbook  = writer.book
		worksheet = writer.sheets['Sheet1']
		worksheet.freeze_panes(1,0)

		os.remove('results.xlsx')
		writer.close()

		return ' '.join(for_printing)