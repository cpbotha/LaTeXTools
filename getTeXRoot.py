import os.path, re

# Parse magic comments to retrieve TEX root
# Stops searching for magic comments at first non-comment line of file
# Returns root file or current file

# Contributed by Sam Finn

def get_tex_root(view):
	# (cpbotha modified)
	# this used to just get the TEXroot verbatim from the project file.
	# it would have been great to have this spec relative to the location
	# of the project file. however, that doesn't seem to be available, so
	# we're going to go for relative to the tex file that's being edited.
	# this is optional however: if you specify an absolute path this will
	# also work.

	# first get directory containing the tex file currenty being edited
	cur_file_dir = os.path.abspath(os.path.dirname(view.file_name()))
	# get the spec from the project settings
	texrootrel = view.settings().get('TEXroot')
	# mash it up with the dir, then get its absolute version
	# if the user has specified an absolute path, that should still take 
	# precedence
	texroot = os.path.abspath(os.path.join(cur_file_dir, texrootrel))

	if os.path.isfile(texroot):
		print "Main file defined in project settings : " + texroot
		return texroot


	texFile = view.file_name()
	for line in open(texFile, "rU").readlines():
		if not line.startswith('%'):
			root = texFile
			break
		else:
			# We have a comment match; check for a TEX root match
			mroot = re.match(r"%\s*!TEX\s+root *= *(.*(tex|TEX))\s*$",line)
			if mroot:
				# we have a TEX root match 
				# Break the match into path, file and extension
				# Create TEX root file name
				# If there is a TEX root path, use it
				# If the path is not absolute and a src path exists, pre-pend it
				(texPath, texName) = os.path.split(texFile)
				(rootPath, rootName) = os.path.split(mroot.group(1))
				root = os.path.join(texPath,rootPath,rootName)
				root = os.path.normpath(root)
				break
	return root