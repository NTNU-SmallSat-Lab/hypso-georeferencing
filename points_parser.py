
from pyproj import Transformer
import rasterio
import csv
import skimage
import numpy as np
import os

# TODO: Update QGIS header when CRS is converted


class GCPList(list):

    def __init__(self, filename, crs='epsg:4326', mode=None):

        super().__init__()


        self.filename = filename
        self.crs = crs

        if mode is None:
            self.mode = self._detect_mode()

        self.gcps = self._load_gcps()

    def _detect_mode(self):

        detected_mode = 'standard'

        modes = ['bin3', 'scale3']

        for mode in modes:
            if '-' + mode in self.filename:
                detected_mode = mode
            
        print('No mode provided. Detected mode: ' + detected_mode)

        return detected_mode

    def _load_gcps(self):

        pcsv = PointsCSV(self.filename)

        header, fieldnames, unproc_gcps = pcsv.read_points_csv()

        for unproc_gcp in unproc_gcps:

            gcp = GCP(**unproc_gcp, crs=self.crs)

            self.append(gcp)


    def save(self):

         
        self._update_filename()
        
        print(self.filename)

        # TODO: write .points file
        #pcsv = PointsCSV(self.filename)

        #pcsv.write_points_csv(gcps=self)



    def _update_filename(self):

        # Split the path from the filename
        path, file = os.path.split(self.filename)

        # Drop the file extension
        base, extension = file.rsplit('.', 1)

        match self.mode:

            case 'standard':

                basename = base
                self.filename = basename + '.points'

            case 'bin3':
                
                # Find the position of the '-bin' string
                bin_index = base.find('-' + 'bin3')

                # Get the part of the filename before '-bin'
                if bin_index != -1:
                    basename = base[:bin_index]

                self.filename = basename + '-bin3.points'

            case 'scale3':

                # Find the position of the '-bin' string
                bin_index = base.find('-' + 'scale3')

                # Get the part of the filename before '-bin'
                if bin_index != -1:
                    basename = base[:bin_index]

                self.filename = basename + '-scale3.points'

        print(self.filename)




    def _get_basename(self):

        # Drop the file extension
        base, extension = self.filename.rsplit('.', 1)

        # Find the position of the '-bin' string
        bin_index = base.find('-bin3')

        # Get the part of the filename before '-bin'
        if bin_index != -1:
            result = base[:bin_index]
        else:
            result = base  # If '-bin' is not found, return the original filename

        return result

    def convert_crs(self, dst_crs=None):

        if dst_crs is not None:
        
            for gcp in self:

                gcp.convert_gcp_crs(dst_crs)

    
    def change_mode(self, dst_mode=None):

        match self.mode:

            case 'standard':

                match dst_mode:

                    case 'bin3':
                        self._standard_to_bin3_mode()

                    case 'scale3':
                        self._standard_to_scale3_mode()

                return

            case 'bin3':
                
                match dst_mode:

                    case 'standard':
                        self._bin3_to_standard_mode()

                    case 'scale3':
                        self._bin3_to_scale3_mode()

                return

            case 'scale3':

                match dst_mode:

                    case 'standard':
                        self._scale3_to_standard_mode()

                    case 'bin3':
                        self._scale3_to_bin3_mode()

                return
    

    # standard mode conversion functons

    def _standard_to_bin3_mode(self):
        for idx, gcp in enumerate(self):

            # Apply binning
            gcp['sourceY'] = gcp['sourceY'] / 3

            # Update GCP
            self[idx] = GCP(**gcp, crs=gcp.crs)

        self.mode = 'bin3'

    def _standard_to_scale3_mode(self):

        for idx, gcp in enumerate(self):

            # Apply scaling
            gcp['sourceX'] = gcp['sourceX'] * 3

            # Update GCP
            self[idx] = GCP(**gcp, crs=gcp.crs)

        self.mode = 'scale3'

    # bin3 mode conversion functions

    def _bin3_to_standard_mode(self):
                
        for idx, gcp in enumerate(self):

            # Apply scaling
            gcp['sourceY'] = gcp['sourceY'] * 3

            # Update GCP
            self[idx] = GCP(**gcp, crs=gcp.crs)

        self.mode = 'standard'

    def _bin3_to_scale3_mode(self):
        
        for idx, gcp in enumerate(self):

            # Apply scaling
            gcp['sourceX'] = gcp['sourceX'] * 3
            gcp['sourceY'] = gcp['sourceY'] * 3

            # Update GCP
            self[idx] = GCP(**gcp, crs=gcp.crs)

        self.mode = 'scale3'

    # scale3 mode conversion functions

    def _scale3_to_standard_mode(self):
        
        for idx, gcp in enumerate(self):

            # Apply scaling
            gcp['sourceX'] = gcp['sourceX'] / 3

            # Update GCP
            self[idx] = GCP(**gcp, crs=gcp.crs)

        self.mode = 'standard'

    def _scale3_to_bin3_mode(self):
        
        for idx, gcp in enumerate(self):

            # Apply scaling
            gcp['sourceX'] = gcp['sourceX'] / 3
            gcp['sourceY'] = gcp['sourceY'] / 3

            # Update GCP
            self[idx] = GCP(**gcp, crs=gcp.crs)

        self.mode = 'bin3'


class GCP(dict):

    def __init__(self, mapX, mapY, sourceX, sourceY, enable=1, dX=0, dY=0, residual=0, crs='epsg:4326'):

        # Initialize dict
        super().__init__(mapX=mapX,
                         mapY=mapY,
                         sourceX=sourceX,
                         sourceY=sourceY,
                         enable=enable,
                         dX=dX,
                         dY=dY,
                         residual=residual)

        self.crs=crs

        # Add rasterio GCP
        self.gcp = rasterio.control.GroundControlPoint(row=self['sourceX'],
                                                        col=self['sourceY'], 
                                                        x=self['mapX'], 
                                                        y=self['mapY'])


    def convert_gcp_crs(self, dst_crs):

        src_crs = self.crs

        if src_crs.lower() != dst_crs.lower():

            # Initialize transformer for CRS conversion
            transformer = Transformer.from_crs(src_crs, dst_crs)

            # mapX is lon
            # mapY is lat

            lon = self['mapX']
            lat = self['mapY']

            lat, lon = transformer.transform(lon, lat)

            self['mapX'] = lon
            self['mapY'] = lat

            # Update rasterio GCP
            self.gcp = rasterio.control.GroundControlPoint(row=self['sourceX'],
                                                            col=self['sourceY'], 
                                                            x=self['mapX'], 
                                                            y=self['mapY'])

            self.crs = dst_crs


class PointsCSV():

    def __init__(self, filename):

        self.filename = filename
        #self.header = None
        #self.labels = None
        #self.unproc_gcps = None
        
        self.default_header = '#CRS: GEOGCRS["WGS 84",ENSEMBLE["World Geodetic System 1984 ensemble",MEMBER["World Geodetic System 1984 (Transit)"],MEMBER["World Geodetic System 1984 (G730)"],MEMBER["World Geodetic System 1984 (G873)"],MEMBER["World Geodetic System 1984 (G1150)"],MEMBER["World Geodetic System 1984 (G1674)"],MEMBER["World Geodetic System 1984 (G1762)"],ELLIPSOID["WGS 84",6378137,298.257223563,LENGTHUNIT["metre",1]],ENSEMBLEACCURACY[2.0]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],CS[ellipsoidal,2],AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],USAGE[SCOPE["Horizontal component of 3D system."],AREA["World."],BBOX[-90,-180,90,180]],ID["EPSG",4326]]'
        self.default_fieldnames = 'mapX,mapY,sourceX,sourceY,enable,dX,dY,residual'
        self.default_fieldnames_list = ['mapX', 'mapY', 'sourceX', 'sourceY', 'enable', 'dX', 'dY', 'residual']



    def write_points_csv(self, gcps=[]):
        
        with open(self.filename, 'w') as csv_file:

            csv_file.write(self.default_header)
            csv_file.write('\n')
            #csv_file.write(self.default_fieldnames)
            #csv_file.write('\n')

            #writer = csv.writer(csv_file, delimiter=',')
            #writer.writerow(['Spam'] * 5 + ['Baked Beans'])
            #writer.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])

            # Open CSV file for writing
            writer = csv.DictWriter(csv_file, 
                                    fieldnames=self.default_fieldnames_list)
            
            writer.writeheader()

            if len(gcps) > 0:

                for gcp in gcps:
                    writer.writerow(gcp)


            # Close file
            csv_file.close()
                    #writer = csv.writer(csv_file, delimiter=',')
            #writer.writerow(['Spam'] * 5 + ['Baked Beans'])
            #writer.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])

    def read_points_csv(self):

        # Unprocessed GCPs list
        unproc_gcps = []

        with open(self.filename, 'r') as csv_file:

            header = csv_file.readline().rstrip()
            fieldnames = csv_file.readline().rstrip()

            # Open CSV file for reading
            reader = csv.DictReader(csv_file, 
                                    fieldnames=self.default_fieldnames_list)

            # Iterate through rows
            for line in reader:

                # Convert to int/floats
                for key, value in line.items():
                    try:
                        line[key] = int(value)
                    except ValueError:
                        try:
                            line[key] = float(value)
                        except ValueError:
                            pass

                # Add line to unprocessed GCPs list
                unproc_gcps.append(line)

            # Close file
            csv_file.close()

        #self.header = header
        #self.fieldnames = fieldnames
        #self.unproc_gcps = unproc_gcps 

        return header, fieldnames, unproc_gcps 





'''
f = '/home/cameron/Nedlastinger/Frohavet/frohavet_2024-04-15_1006Z-original-bin3.points'
y = GCPList(f)

print(y.mode)

y.change_mode(dst_mode='scale3')

print(y.mode)

y.save()

#y.change_mode(dst_mode='')
'''