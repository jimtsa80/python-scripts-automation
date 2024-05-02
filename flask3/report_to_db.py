# -*- coding: UTF-8 -*-

import sys
import glob
import os
import csv
import pandas as pd
import pymysql

class Report_to_db():
	
	def __init__(self):
		self.db = pymysql.connect(host='localhost',
			user='isieve',
			passwd='isieve',
			db='cricketAus')

		self.dfs = []
		self.mydict = {}
		self.valuelist = []

	def import_report(self, folder):

		csvfiles = glob.glob(os.path.join(folder, "*.*"))

		i = 0
		for csvfile in csvfiles:
			print(os.path.split(csvfile)[1])
			if 'xls' in csvfile:
				df = pd.read_excel(csvfile, ignore_index=True)
			else:
				df = pd.read_csv(csvfile, sep='\t', ignore_index=True)

			df['Filename'] = os.path.split(csvfile)[1].split('-')[0]

			self.dfs = df.values.tolist()

			with self.db.cursor() as cursor:

				for row in self.dfs:
					
					sql = """INSERT INTO BBL(brand, location, time, duration, place, size, total, avg, frame, filename) VALUES \
											(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
					val = (row[0].strip(), row[1].strip(), row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9])
					
					try:
						i += 1
						cursor.execute(sql, val)
						self.db.commit()
					except Exception as e:
						print("Dublicate Entry was detected")

		return 'There are %r new entries from %r files' % (i, len(csvfiles))

	def queries(self, project, brand):

		with self.db.cursor() as cursor:

			if brand == '':
				sql2 = """SELECT DISTINCT concat(brand, '_', location) as br_loc from %s"""%(project)
				cursor.execute(sql2)
			else:
				sql1 = """SELECT DISTINCT concat(brand, '_', location) as br_loc from %s where brand like '%s'"""%(project, '%'+brand+'%')
				cursor.execute(sql1)

			for i, rows in enumerate(cursor):
				if i == 0: 
					continue
				k = rows[0].split('_')[0]
				v = rows[0].split('_')[1]
				self.valuelist.extend([v])
				if not k in self.mydict:
					self.mydict[k] = [v]
				else:
					self.mydict[k].append(v)

		unique_keys = [k for k,v in self.mydict.items() if list(self.mydict.keys()).count(k)==1]
		print("Total Brands: " + str(len(unique_keys)))
		self.valuelist = sorted(set(self.valuelist))
		print("Total Touchpoints: " + str(len(self.valuelist)))

		with open('final_output.txt', 'w') as f:
			writer = csv.writer(f, delimiter='\n', lineterminator="\n")
			for k, v in self.mydict.items():
				writer.writerow(['#'+k]+ sorted(v))

		return "The txt is ready! Total Brands: %r Total Touchpoints: %r" % (len(unique_keys), len(self.valuelist))




				

			







