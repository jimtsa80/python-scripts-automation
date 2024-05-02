# -*- coding: UTF-8 -*-

from __future__ import division
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import sys
import itertools
import string
import time
from datetime import datetime
import math

class Check_videos():

	def write_spreadsheet(self, sheet, worksheet, data, start_row):
		try:
			scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
			creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
			client = gspread.authorize(creds)

			sheet = client.open(sheet)
			worksheet = sheet.worksheet(worksheet)
			
			start_letter = 'A'
			end_letter = string.uppercase[len(data[0]) - 1]
			end_row = start_row + len(data) - 1
			range = "%s%d:%s%d" % (start_letter, start_row, end_letter, end_row)
			cell_list = worksheet.range(range)
		
			idx = 0
			for (start_row, rowlist) in enumerate(data):
				for (colnum, value) in enumerate(rowlist):
					cell_list[idx].value = value
					idx += 1
					if idx >= len(cell_list):
						break

			worksheet.update_cells(cell_list)

		except Exception as e:
			print(e)

	def processing(self, date1, date2):
		
		pd.options.mode.chained_assignment = None

		scope = ['https://spreadsheets.google.com/feeds']
		creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
		client = gspread.authorize(creds)

		working_videos = client.open('all_video_footage')
		working_videos_wsheets = working_videos.worksheets()
		wsheets = len(working_videos_wsheets)

		history_videos = client.open('DB_past_videos_footage')
		wsheet1 = history_videos.sheet1
		df1 = get_as_dataframe(wsheet1)

		row_toWrite = len(df1[df1.columns[0:1]].values) + 2

		for i in range(wsheets):

			wsheet = working_videos.get_worksheet(i)
			df = get_as_dataframe(wsheet, evaluate_formulas=True, skiprows=1, header=None, parse_dates=True)
			df_filtered = df[df[7] != 1]
			if df_filtered.empty:
				print('No new entries found in', wsheet.title)
			else:
				start_date = datetime.strptime(date1, '%d/%m/%Y').strftime('%Y-%m-%d')
				end_date = datetime.strptime(date2, '%d/%m/%Y').strftime('%Y-%m-%d')
				df_filtered[5] = pd.to_datetime(df_filtered[5], dayfirst=True)
				
				df_range = df_filtered[df_filtered[5].between(start_date, end_date)]
				
				df_groupby = df_range.groupby([4])[3].sum()
				
				annotators = df_groupby.index.values.tolist()
				try:
					footage = df_groupby.values.astype(int).tolist()
				except Exception as e:
					print(e)
					continue

				if len(footage) == 0:
					print('No entries from', wsheet.title)
				else:
					print('Entries from', wsheet.title)
					if math.isnan(df[7][0]):
						cell_list = wsheet.range('H2:H'+str(len(df_range)+1))
						for cell in cell_list:
							cell.value = '1'
						wsheet.update_cells(cell_list)
					else:
						start = int(df[7].sum()+1)
						new_lines = len(df_range)
						end = start + new_lines
						cell_list = wsheet.range('H'+str(start)+':H'+str(end))

						for cell in cell_list:
							cell.value = '1'

						wsheet.update_cells(cell_list)

					entries = []
					for a, b in itertools.izip(annotators, footage):
						entries.append([a,b])
					
					for entry in entries:
						ent = ",".join(str(e) for e in entry)
						annotator = ent.split(',')[0]
						duration = ent.split(',')[1]
						self.write_spreadsheet('DB_past_videos_footage', 'all_videos', [[time.strftime("%d/%m/%Y"), wsheet.title, annotator, duration, start_date]], row_toWrite)
						row_toWrite += 1

		df1 = get_as_dataframe(wsheet1, evaluate_formulas=True, skiprows=1, header=None, parse_dates=True)

		df1[4] = pd.to_datetime(df1[4], dayfirst=True)
		df1_filtered = df1[df1[4] == start_date]

		df_groupby_projects = df1_filtered.groupby([1])[3].sum()
		projects = df_groupby_projects.index.values.tolist()
		total_footage = df_groupby_projects.values.astype(int).tolist()

		wsheet2 = history_videos.get_worksheet(1)
		df2 = get_as_dataframe(wsheet2)
		row_toWrite2 = len(df2[df2.columns[0:1]].values) + 2

		entries_proj = []
		for a, b in itertools.izip(projects, total_footage):
			entries_proj.append([a,b])

		for entry in entries_proj:
			proj = entry[0]
			total_duration = entry[1]
			self.write_spreadsheet('DB_past_videos_footage', 'projects', [[datetime.strptime(start_date, '%Y-%m-%d').strftime('%d/%m/%Y'), proj, total_duration, total_duration/3600]], row_toWrite2)
			row_toWrite2 += 1

		df_groupby_annotators = df1_filtered.groupby([2])[3].sum()
		annotators_total = df_groupby_annotators.index.values.tolist()
		total_anno_footage = df_groupby_annotators.values.astype(int).tolist()

		df_groupby_annotators1 = df1_filtered.groupby([2])[1].apply(list)
		proj_per_anno = df_groupby_annotators1.values.tolist()

		wsheet3 = history_videos.get_worksheet(2)
		df3 = get_as_dataframe(wsheet3)
		row_toWrite3 = len(df3[df3.columns[0:1]].values) + 2

		entries_anno = []
		for a, b, c in itertools.izip(annotators_total, total_anno_footage, proj_per_anno):
			entries_anno.append([a,b,c])

		for entry in entries_anno:
			anno = entry[0]
			total_anno_duration = entry[1]
			anno_proj = ",".join(entry[2])
			self.write_spreadsheet('DB_past_videos_footage', 'annotators', [[datetime.strptime(start_date, '%Y-%m-%d').strftime('%d/%m/%Y'), anno, total_anno_duration, total_anno_duration/3600, anno_proj]], row_toWrite3)
			row_toWrite3 += 1