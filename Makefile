setup:
	pip install -r requirements.txt

pipeline: 
	python load_data.py
	python pipeline/initial_analysis.py
	python pipeline/statistical_analysis.py
	python pipeline/data_subset_analysis.py	

dashboard:
	streamlit run dashboard/app.py