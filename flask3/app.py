# -*- coding: utf-8 -*-

import os
import glob
import sys
import zipfile
import pandas as pd
# from pandas.io.excel import ExcelWriter
from flask import Flask, flash, request, redirect, url_for, render_template, Markup
from werkzeug.utils import secure_filename
from socialMedia_parser import Social_parser
from xlsx_creator import Xlsx_creator
from rep_creator import Report_creator
from check_videos import Check_videos
from moirasies import Moirasies
# from photo_press import Photo_press
from report_to_db import Report_to_db

# reload(sys)
# sys.setdefaultencoding('utf8')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['csv', 'xml', 'zip', 'xls', 'xlsx'])

app = Flask(__name__)
app.secret_key = 'super secret key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
@app.route('/social_mention.html', methods=['GET', 'POST'])
def social_mention():
	page = 'social'
	if request.method == 'POST':
		if 'article' not in request.files and 'ontology' not in request.files:
			flash('No file part')
			return redirect(request.url)

		article = request.files['article']
		ontology = request.files['ontology']
		delimiter = request.form['delimiter']

		if article.filename == '' and ontology.filename == '':
			flash('No selected file')
			return redirect(request.url)

		if article and ontology and allowed_file(article.filename) and allowed_file(ontology.filename):
			art_filename = secure_filename(article.filename)
			ont_filename = secure_filename(ontology.filename)
			article.save(os.path.join(app.config['UPLOAD_FOLDER'], art_filename))
			ontology.save(os.path.join(app.config['UPLOAD_FOLDER'], ont_filename))

		if article.filename != '' and ontology.filename != '':
			flash('The file has successfully uploaded!')

		mention = Social_parser(os.path.join(os.getcwd(), UPLOAD_FOLDER, ont_filename))
		
		if 'press' in art_filename:
			xlsx = pd.read_excel(os.path.join(os.getcwd(), UPLOAD_FOLDER, art_filename), index_col=None)
			xlsx.to_csv('press_results.csv', encoding='utf-8', index=False)

		if 'press' in art_filename:
			for a in mention.get_mention('press_results.csv', delimiter):
				flash("{: >20} {: >20}".format(' '.join(a.split()[:-1]), str(a.split()[-1])))
		else:
			for a in mention.get_mention(os.path.join(os.getcwd(), UPLOAD_FOLDER, art_filename), delimiter):
				flash("{: >20} {: >20}".format(' '.join(a.split()[:-1]), str(a.split()[-1])))

	# for_empty_folder = glob.glob(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], "*.*"))
	# if len(for_empty_folder) > 0:
	# 	for fl in for_empty_folder:
	# 		os.remove(fl)

	return render_template('social_mention.html', page=page)

@app.route('/xlsx_creator.html', methods=['GET', 'POST'])
def xlsx_creator():
	#1sxolio
	page = 'xlsx'

	if request.method =='POST':
		
		if 'file[]' in request.files:
			uploaded_files = request.files.getlist("file[]")
			use = request.form['use']
			fname = request.form['filename']

			success = 0
			for file in uploaded_files:
				if allowed_file(file.filename):
					filename = secure_filename(os.path.split(file.filename)[1])
					
					if 'report' in filename:
						report_filename = filename
						file.save(os.path.join(os.getcwd(), filename))
					elif 'zip' in filename:
						
						file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))

						with zipfile.ZipFile(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], filename), 'r') as zip_ref:
							zip_ref.extractall(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER']))

						combined_csv = pd.concat([pd.read_csv(f, error_bad_lines=False) for f in glob.glob(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], '*.csv'))])
						for infile in glob.glob(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], '*.csv')):
							os.remove(infile)
						combined_csv.to_csv(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], report_filename.replace('report.xls', '')+'images.csv'), index=False)
					else:
						file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
						
					if file:
						success += 1
						if success == len(uploaded_files):
							flash(str(success)+ ' ' +'files have successfully uploaded!')
			
		elif 'pressZip' in request.files:
			press_file = request.files['pressZip']
			use = request.form['use']
			fname = request.form['filename']
			press_file_filename = secure_filename(press_file.filename)
			press_file.save(os.path.join(os.getcwd(), press_file_filename))

			with zipfile.ZipFile(os.path.join(os.getcwd(), press_file_filename), 'r') as zip_ref:
				zip_ref.extractall(os.getcwd())
		else:
			flash('No file part')
			return redirect(request.url)

		if use == 'pressEva':
			ph_press = Photo_press()

			ph_press.getSize2(os.path.join(os.getcwd(), 'photos'))
			ph_press.getSize1(os.path.join(os.getcwd(), 'pages'))
			ph_press.photo_tab_creator()
			ph_press.metadata(os.path.join(os.getcwd(), 'photos'))

			df_art = pd.read_csv('art_tab.csv')
			df_art['Date'] = pd.to_datetime(df_art['Date'])
			df_art['Date'] = df_art['Date'].dt.strftime('%d/%m/%Y')
			df_art.to_csv('new_art_tab.csv', encoding='utf-8', index=False)

			csvs = ['new_art_tab.csv', 'text_tab.csv', 'photo_tab.csv']

			with ExcelWriter(str(os.path.join(os.getcwd(), 'photos'))+'_final.xlsx', date_format='dd/mm/yyyy') as ew:
				for csv in csvs:
					if 'art' in csv:
						pd.read_csv(csv, encoding='utf-8', usecols = ['ArtID', 'Newspaper', 'Title','Date',	'WC','PN','Front/Back']).to_excel(ew, sheet_name=csv.split('.')[0], index=None)
					else:
						pd.read_csv(csv, encoding='utf-8', ).to_excel(ew, sheet_name=csv.split('.')[0], index=None)

			# writer = ExcelWriter(str(os.path.join(os.getcwd(), 'photos'))+'_final.xlsx', engine='xlsxwriter')
			# for csv in csvs:
			# 	if 'art' in csv:
			# 		df = pd.read_csv(csv, encoding='utf-8', usecols = ['ArtID', 'Newspaper', 'Title','Date','WC','PN','Front/Back'])
			# 		pd.formats.format.header_style = None
			# 		df.to_excel(writer, csv.split('.')[0], index=None)

			# 		workbook  = writer.book
			# 		worksheet = writer.sheets[csv.split('.')[0]]

			# 		format1 = workbook.add_format({'num_format': 'dd/mm/yyyy'})
			# 		worksheet.set_column('D:D', None, format1)

			# 	else:
			# 		df = pd.read_csv(csv, encoding='utf-8')
			# 		df.to_excel(writer, csv.split('.')[0], index=None)

			# workbook.close()
			# writer.save()

			flash('Photos metadata and press report are ready!')
		else:
			xlsx_create = Xlsx_creator()

			if use == 'concat':
				for rec in xlsx_create.take_arguments(os.path.join(app.config['UPLOAD_FOLDER']), use, fname):
					flash(rec)
				xlsx_create.finalize()
				flash('The report is ready!')

			elif use == 'multic':
				for rec in xlsx_create.take_arguments(os.path.join(app.config['UPLOAD_FOLDER']), use, fname):
					flash(rec)
				xlsx_create.finalize()
				flash('The reports are ready!')

			elif use == 'webvideos':
				for rec in xlsx_create.take_arguments(os.path.join(app.config['UPLOAD_FOLDER']), use, fname):
					flash(rec)
				flash('The report is ready!')
			else:
				if use != 'web':
					for rec in xlsx_create.take_arguments(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER']), use, fname):
						flash(rec)
					xlsx_create.finalize()
					flash('The report is ready!')
				else:
					i = 0
					for a, b in zip(glob.glob(os.path.join(os.getcwd(), '*.xls*')), glob.glob(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], '*.csv'))):
						i += 1
						for rec in xlsx_create.take_arguments(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER']), use, b, len(glob.glob(os.path.join(os.getcwd(), '*.xls*')))):
							flash(rec)

						if use == 'web':
							xlsx_create.finalreport(a)
				
					flash(str(i)+' report(s) are ready!')
					xlsx_create.finalize()

			message = Markup("<a href='http://192.168.7.64/flask/' target='_blank'>Find the results here</a>")
			flash(message)

	for_empty_folder = glob.glob(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], "*.xlsx"))
	if len(for_empty_folder) > 0:
		for fl in for_empty_folder:
			try:
				os.rename(os.path.join(app.config['UPLOAD_FOLDER'], os.path.split(fl)[1]), os.path.split(fl)[1])
			except WindowsError:
				for f in glob.glob(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], "*.*")):
					os.remove(f)
				for f in glob.glob(os.path.join(os.getcwd(), "*.xlsx")):
					os.remove(f)
				message = Markup("<h3>All the previous uploaded files have beed deleted! Please upload once more time</h3>")
				flash(message)

	return render_template('xlsx_creator.html', page=page)

@app.route('/report_creator.html', methods=['GET', 'POST'])
def report_creator():
	page = 'report'

	if request.method == 'POST':
		cond1 = 'article' not in request.files and 'photocsv' not in request.files
		cond2 = 'article' not in request.files and 'zipfile' not in request.files
		if cond1 or cond2 is True:
			flash('No file part')
			return redirect(request.url)

		article = request.files['article']
		if request.files['ont'].filename != '':
			ont = request.files['ont']

		#print(article.filename, request.files['photocsv'].filename, request.files['zipfile'].filename)

		#if 'photocsv' in request.files:
		if request.files['photocsv'].filename != '':
			photocsv = request.files['photocsv']
		else:
			zipfile = request.files['zipfile']
		delimiter = request.form['delimiter']

		cond3 = article.filename == '' and photocsv.filename == ''
		cond4 = article.filename == '' and zipfile.filename == ''
		if cond3 or cond4 is True:
			flash('No selected file')
			return redirect(request.url)

		# if 'photocsv' in request.files:
		if request.files['photocsv'].filename != '':
			art_filename = secure_filename(article.filename)
			photocsv_filename = secure_filename(photocsv.filename)
			article.save(os.path.join(os.getcwd(), art_filename))
			photocsv.save(os.path.join(os.getcwd(), photocsv_filename))

		else:
			if cond2 is False:
				if article and zipfile and allowed_file(article.filename) and allowed_file(zipfile.filename):
					art_filename = secure_filename(article.filename)
					zipfile_filename = secure_filename(zipfile.filename)
					article.save(os.path.join(os.getcwd(), art_filename))
					zipfile.save(os.path.join(os.getcwd(), zipfile_filename))

		# if 'ont' in request.files:
		if request.files['ont'].filename != '':
			ont_filename = secure_filename(ont.filename)
			ont.save(os.path.join(os.getcwd(), ont_filename))

		create = Report_creator()

		if request.files['photocsv'].filename != '':
			for rec in create.creator(art_filename, photocsv_filename, delimiter):
				flash(rec)
		else:
			for rec in create.creator(art_filename, 'no', delimiter, zipfile_filename):
				flash(rec)
			
		flash(create.finalreport())

		if request.files['ont'].filename != '':
			print('An export ontology was detected')
			flash('An export ontology was detected')
			flash(create.creator_nascar(ont_filename))

		message = Markup("<a href='http://192.168.7.64/flask/' target='_blank'>Find the results here</a>")
		flash(message)

	return render_template('report_creator.html', page=page)

@app.route('/check_week_videos.html', methods=['GET', 'POST'])
def check_week_videos():

	page = 'check_videos'

	if request.method =='POST':
		case1 = request.form['date1'] == '' or request.form['date2'] == ''
		case2 = request.form['start'] == '' or request.form['stop'] == '' or request.form['atoma'] == ''
	
		if case1 ==  False:
		
			date1 = request.form['date1']
			date2 = request.form['date2']

			check = Check_videos()

			check.processing(date1, date2)
			message = Markup("<a href='https://docs.google.com/spreadsheets/d/1_vgFdsXonisb073Li2Rwj_5qbUwnNWT-bjE8Qg9WJvs/edit#gid=0' target='_blank'>Find the results here</a>")
			flash(message)
		
		elif case2 == False:

			start = request.form['start']
			stop = request.form['stop']
			atoma = request.form['atoma']

			print(start, stop, atoma)

			moirasia = Moirasies()

			for i in moirasia.main(start, stop, atoma):
				flash(''.join(str(i).replace('[', '').replace(']', '').replace(',', '\t')))


		else:
			flash('No file part')
			return redirect(request.url)

	return render_template('check_week_videos.html', page=page)


@app.route('/report_to_db.html', methods=['GET', 'POST'])
def report_to_db():

	page = 'report_to_db'
	import_db = Report_to_db()

	if request.method =='POST':
		
		if 'file[]' in request.files:
			uploaded_files = request.files.getlist("file[]")

			success = 0
			for file in uploaded_files:
				if allowed_file(file.filename):
					filename = secure_filename(os.path.split(file.filename)[1])
					file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))

					if file:
						success += 1
						if success == len(uploaded_files):
							flash(str(success)+ ' ' +'files have successfully uploaded!')

			
			flash(import_db.import_report(app.config['UPLOAD_FOLDER']))

		elif request.form['project'] != '' or request.form['brand'] != '':

			project = request.form['project']
			brand = request.form['brand']

			flash(import_db.queries(project, brand))

		else:
			flash('No file part')
			return redirect(request.url)


	return render_template('report_to_db.html', page=page)

if __name__ == '__main__':
	app.run(debug = True, threaded=True)