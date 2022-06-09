from flask import Flask, redirect, render_template, request
from flask_sqlalchemy import SQLAlchemy
import numpy as np
import random
import json
import os

num_production_orders = 100
proposed_layout = False
create_production_order_data = False
# proposed_layout handler is there as the html text dont update when proposed layout is clicked,
# therefore layout has to be extracted from the updated temp file

def findPermutations(string, index, n, storing_list):
	""" Returns all possible permutations constrained within adjacent swapping of elements
	:param string: list of strings
	:type string: list
	:param index: starting index
	:type index: int
	:param n: length of list
	:type n: int
	:param storing_list: empty list to store results
	:type storing_list: list
	...
	:return: list of permutations
	:rtype: list
	...
	input: ['A', 'B', 'C']
	output: ['A.B.C', 'A.C.B', 'B.A.C']
	"""
	if index >= n or (index + 1) >= n:
		storing_list.append('.'.join(string))
		return
	findPermutations(string, index + 1, n, storing_list)
	string[index], string[index + 1] = string[index + 1], string[index]     
	findPermutations(string, index + 2, n, storing_list)
	string[index], string[index + 1] = string[index + 1], string[index]

def craft_iteration(layout_order):
	""" Performs CRAFT Heuristic
	:param layout_order: order at which departments are configured
	:type layout_order: list
	...
	:return: layout with the minimum material average distance, average material distance associated with the proposed layout
	:rtype: list, str
	"""
	pairwise_flow_file = open("./datasets/pairwise_flow.json", "r")
	pairwise_flow_dict = json.load(pairwise_flow_file)
	inversions, distances = [], []
	layout_order = layout_order[1:-1]
	findPermutations(layout_order, 0, len(layout_order), inversions)
	inversions = sorted(list(set(inversions)))
	for inversion in inversions:
		inversion = ['A'] + inversion.split('.') + ['L']
		layout_array = np.array(inversion).reshape(3,4).tolist()
		distance = material_distance(layout_array, pairwise_flow_dict)/num_production_orders
		distances.append(float(distance))
	index_min = np.argmin(distances)
	new_layout = ['A'] + inversions[index_min].split('.') + ['L']
	new_distance = distances[index_min]
	return new_layout, str(round(new_distance,2))

def make_production_orders(num_orders=num_production_orders):
	""" Creates dummy production orders
	:param num_orders: number of dummy orders to create
	:type num_ordesr: int
	...
	:return: production order number and its material flow sequence
	:rtype: dict
	"""
	prod_order_sequence = {}
	for order in range(num_orders):
		production_order_number = random.randint(10000,99999)
		if production_order_number in prod_order_sequence.keys():
			continue
		machines_available = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
		number_movement = random.randint(1,10)
		production_sequence = ['A'] + random.sample(machines_available, number_movement) + ['L']
		prod_order_sequence[production_order_number] = production_sequence
	return prod_order_sequence

def store_order(order):
	""" stores proposed layout into db, with relevant HTML CONFIG
	:param order: order at which departments are configured
	:type order: list
	"""
	db.session.query(layout_configurations).delete()
	db.session.commit()
	for department_name in order:
		html_name = department_name
		if department_name == 'A' or department_name == 'L':
			html_hex = "#F88379"
			draggable = 'false'
		else:
			html_hex = "#ffce56"
			draggable = 'true'
		new_configuration = layout_configurations(html_name=html_name, html_id=html_name, html_hex=html_hex, draggable=draggable)
		db.session.add(new_configuration)
		db.session.commit()

def store_pairwise_flows(production_orders):
	""" Compiles number of instance where material flowed from one work center to another
	:param production_orders: all production orders
	:type production_orders: list
	...
	:return: pairwise work center mapping, and the number of flow between the two work centers
	:rtype: dict
	"""
	pairwise_flows = {}
	for production_order in production_orders:
		for index in range(1,len(production_order)):
			pair = production_order[index-1] + ',' + production_order[index]
			if pair in pairwise_flows.keys():
				pairwise_flows[pair] += 1
			else:
				pairwise_flows[pair] = 1
	return pairwise_flows

def find_in_list_of_list(mylist, char):
	""" Determines index of element in a two-dimensional list
	:param my_list: two-dimensional list (layout)
	:type my_list: list
	:param char: element of interest
	:type char: string
	...
	:return: row and column index of element
	:rtype: tuple
	"""
	for sub_list in mylist:
		if char in sub_list:
			return (mylist.index(sub_list), sub_list.index(char))
	raise ValueError("'{char}' is not in list".format(char = char))

def material_distance(layout, pairwise_flow):
	""" Computes total material distance for all material flows in a particular layout
	:param layout: two-dimensional list of selected layout
	:type layout: list
	:param pairwise_flow: compiled instances of pairwise material flow
	:type pairwise_flow: dict
	...
	:return: total material distance
	:rtype: float
	"""
	total_distance = 0
	for pair, instance in pairwise_flow.items():
		mach_1, mach_2 = pair.split(',')[0], pair.split(',')[1]
		mach_1_pos, mach_2_pos = find_in_list_of_list(layout, mach_1), find_in_list_of_list(layout, mach_2)
		rect_distance = np.abs(mach_1_pos[0]-mach_2_pos[0]) + np.abs(mach_1_pos[1]-mach_2_pos[1])
		distance = rect_distance * instance
		total_distance += distance
	return total_distance

app = Flask(__name__)
IS_DEV = app.env == 'development'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///datasets/production_sequence.db'
app.config['SQLALCHEMY_BINDS'] = {
	"two": 'sqlite:///datasets/layout_configurations.db',
	"three": 'sqlite:///datasets/layouts.db'
}

db = SQLAlchemy(app)
db.create_all()

class production_sequence(db.Model):
	id = db.Column("id", db.Integer, primary_key=True)
	production_number = db.Column(db.String(200), nullable=False)
	production_order = db.Column(db.String(200), nullable=False)
	
	def __repr__(self):
		return '<Production Sequence %r>' % self.id

class layout_configurations(db.Model):
	__bind_key__ = "two"
	id = db.Column("id", db.Integer, primary_key=True)
	html_name = db.Column(db.String(200), nullable=False)
	html_id = db.Column(db.String(200), nullable=False)
	html_hex = db.Column(db.String(200), nullable=False)
	draggable = db.Column(db.String(200), nullable=False)

	def __repr__(self):
		return '<Configuration %r>' % self.id

class layouts(db.Model):
	id = db.Column("id", db.Integer, primary_key=True)
	name = db.Column(db.String(200), nullable=False)
	distance = db.Column(db.String(100), nullable=False)
	
	def __repr__(self):
		return '<Layout %r>' % self.id

@app.route("/reconfiguration", methods=['GET', 'POST'])
def reconfiguration():
	pairwise_flow_file = open("./datasets/pairwise_flow.json", "r")
	pairwise_flow_dict = json.load(pairwise_flow_file)
	global proposed_layout
	if request.method == 'POST':
		if request.form.get('reset_button') == 'Reset Layout':
			proposed_layout = False
			##### LOAD ORIGINAL LAYOUT
			a_file = open("./datasets/perm_order.json", "r")
			a_dict = json.load(a_file)
			original_list = list(a_dict.values())

			##### UPDATE HTML RENDERING
			store_order(original_list)

			##### UPDATE TEMP FILE WITH ORIGINAL LAYOUT
			b_file = open("./datasets/temp_order.json", "w")
			b_file = json.dump(a_dict, b_file)
			try:
				return redirect(request.url)
			except:
				return 'There was an issue performing the reset'
			
		elif request.form.get('craft_button') == 'Propose Layout':
			proposed_layout = True # set current action to layout proposal

			##### GET PROPOSED LAYOUT
			layout_string = request.form['layout']
			layout_dict = json.loads(layout_string)
			layout_list = list(layout_dict.values())
			proposed_list, distance = craft_iteration(layout_list)

			# ##### UPDATE HTML RENDERING
			store_order(proposed_list)

			# ##### UPDATE TEMP FILE
			proposed_dict = {}
			for index, department in enumerate(proposed_list):
				proposed_dict[index] = department
			a_file = open("./datasets/temp_order.json", "w")
			a_file = json.dump(proposed_dict, a_file)
			layout_display = str(layout_list)
			new_layout = layouts(name=layout_display, distance=distance)
			try:
				db.session.add(new_layout)
				db.session.commit()
				return redirect(request.url)
			except:
				return 'There was an issue adding the proposed layout'

		elif request.form.get('confirm_button') == 'Confirm Layout':
			if proposed_layout:
				a_file = open("./datasets/temp_order.json", "r")
				layout_dict = json.load(a_file)
				global_order = list(layout_dict.values())
				store_order(global_order)
			else:
				layout_string = request.form['layout']
				layout_dict = json.loads(layout_string)
				layout_list = list(layout_dict.values())

				##### UPDATE HTML RENDERING
				global_order = list(layout_list)
				store_order(global_order)

				##### UPDATE TEMP FILE
				a_file = open("./datasets/temp_order.json", "w")
				a_file = json.dump(layout_dict, a_file)

			layout_array = np.array(layout_list).reshape(3,4).tolist()
			distance = material_distance(layout_array, pairwise_flow_dict)/num_production_orders
			layout_display = str(layout_list)
			new_layout = layouts(name=layout_display, distance=distance)
			
			try:
				db.session.add(new_layout)
				db.session.commit()
				return redirect(request.url)
			except:
				return 'There was an issue adding the re-configured layout'
	else:
		proposed_layout = False
		try:
			a_file = open("./datasets/temp_order.json", "r")
			a_dict = json.load(a_file)
			a_string = json.dumps(a_dict).replace(" ", "")
			all_layouts_configurations = layout_configurations.query.all()
			all_layouts = layouts.query.all()
			return render_template("reconfiguration.html", order_layouts=all_layouts_configurations, all_layouts=all_layouts, layout=a_string)
		except:
			a_file = open("./datasets/perm_order.json", "r")
			a_dict = json.load(a_file)
			a_string = json.dumps(a_dict).replace(" ", "")
			a_list = list(a_dict.values())
			store_order(a_list)
			all_layouts = layouts.query.all()
			all_layouts_configurations = layout_configurations.query.all()
			return render_template("reconfiguration.html", order_layouts=all_layouts_configurations, all_layouts=all_layouts, layout=a_string)

@app.route('/delete/<int:id>')
def delete(id):
	layout_to_delete = layouts.query.get_or_404(id)
	try:
		db.session.delete(layout_to_delete)
		db.session.commit()
		return redirect('/reconfiguration')
	except:
		return 'There was a problem deleting that layout'

@app.route("/", methods=['GET', 'POST'])
def home():
	global create_production_order_data
	if request.method == 'POST':
		if request.form.get('change-data-button') == 'Try Another Problem!':
			create_production_order_data = True
			return redirect(request.url)
	else:
		if create_production_order_data:
			db.session.query(production_sequence).delete()
			db.session.commit()
			production_orders = make_production_orders()
			for production_number, production_order in production_orders.items():
				new_production_order = production_sequence(production_number=production_number, production_order=str(production_order))
				db.session.add(new_production_order)
				db.session.commit()
			pairwise_flows = store_pairwise_flows(list(production_orders.values()))
			a_file = open("./datasets/pairwise_flow.json", "w")
			a_file = json.dump(pairwise_flows, a_file)

	production_orders = production_sequence.query.all() # Produciton Order Table
	create_production_order_data = False
	return render_template("home.html", production_orders=production_orders)

@app.route("/about", methods=['GET', 'POST'])
def about():
	return render_template("about.html")

if __name__ == "__main__":
	os.environ['FLASK_ENV'] = 'development'
	app.run(debug=True)