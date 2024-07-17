
#import sys
#sys.path.append('../')
import georeferencing as georeferencing
import os





filename = '/home/cameron/Nedlastinger/Frohavet/frohavet_2024-04-15_1006Z-bin3-original.points'
gcps = georeferencing.GCPList(filename)

#print(gcps)

print(gcps.image_mode)

gcps.change_image_mode(dst_image_mode='standard')

print(gcps.image_mode)

gcps.save()


