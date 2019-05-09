
# Make file compatible with ES bulk
f = open("clinical.json", "r")
newF = open("clinical_bulk.json", "w+")
id = 0

for line in f.readlines():
	id += 1
	newF.write('{ "index" : { "_index" : "tga_clinical", "_id" : "' + str(id) + '" } }\n')	
	newF.write(line)
	
f.close()


	
