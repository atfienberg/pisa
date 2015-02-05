#! /usr/bin/env python
#
# FisherAnalysis.py
#
# Runs the Fisher Analysis method
#
# author: Lukas Schulte - schulte@physik.uni-bonn.de
#         Sebastian Boeser - sboeser@uni-mainz.de
#	  Thomas Ehrhardt - tehrhard@uni-mainz.de

import numpy as np
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import tempfile
import os

from pisa.utils.log import logging, profile, physics, set_verbosity
from pisa.utils.jsons import from_json,to_json
from pisa.analysis.TemplateMaker import TemplateMaker
from pisa.utils.params import select_hierarchy, get_free_params, get_values
from pisa.analysis.fisher.gradients import get_gradients, get_hierarchy_gradients
from pisa.analysis.fisher.BuildFisherMatrix import build_fisher_matrix
from pisa.analysis.fisher.Fisher import FisherMatrix 


parser = ArgumentParser(description='''Runs the Fisher analysis method by varying a number of systematic parameters 
defined in a settings.json file, taking the number of test points from a grid_settings.json file, and saves the
Fisher matrices for the desired hierarchy.''',
                        formatter_class=ArgumentDefaultsHelpFormatter)

parser.add_argument('-t','--template_settings',type=str,
                    metavar='JSONFILE', required = True,
                    help='''Settings related to the template generation and systematics.''')
parser.add_argument('-g','--grid_settings',type=str,
                    metavar='JSONFILE', required = True,
                    help='''Settings for the grid on which the gradients are
                    calculated.''')
parser.add_argument('--normal-truth',action='store_true',
		    default=False, dest='normal_truth',
		    help='Compute Fisher matrix for true normal hierarchy')
parser.add_argument('--inverted-truth',action='store_true',
		    default=False, dest='inverted_truth',
		    help='Compute Fisher matrix for inverted normal hierarchy')

sselect = parser.add_mutually_exclusive_group(required=False)
sselect.add_argument('--save-templates',action='store_true',
                    default=True, dest='save_templates',
                    help="Save all the templates used to obtain the gradients")
sselect.add_argument('--no-save-templates', action='store_false',
                    default=False, dest='save_templates',
                    help="Save just the fiducial templates")
parser.add_argument('-o','--outdir',type=str,default='fisher_data.json',metavar='DIR',
                    help="Output directory")
parser.add_argument('-v', '--verbose', action='count', default=None,
                    help='set verbosity level')
args = parser.parse_args()

set_verbosity(args.verbose)

# Read in the settings
template_settings = from_json(args.template_settings)
# This has only the number of test points in the parameter ranges and the chi2 criterion
grid_settings  = from_json(args.grid_settings)

chosen_data = []
if args.normal_truth:
	chosen_data.append(('data_NMH',True))
if args.inverted_truth:
	chosen_data.append(('data_IMH',False))

# if chosen_data == []:
	
# Here all the templates will be stored (temporarily):
# template_directory = 

# Get the parameters
params = template_settings['params']
bins = template_settings['binning']

# Artifically add the hierarchy parameter to the list of parameters
# The method get_hierarchy_gradients below will know how to deal with it
params['hierarchy_nh'] = { "value": 0., "range": [0.,1.],
                           "fixed": False, "prior": None}
params['hierarchy_ih'] = { "value": 1., "range": [0.,1.],
                           "fixed": False, "prior": None}

# Initialise dictionary to hold Fisher matrices
fisher = {}
 
# Get a template maker with the settings used to initialize
template_maker = TemplateMaker(get_values(params),**bins)

# Generate fiducial templates for both hierarchies (needed for partial derivatives 
# w.r.t. hierarchy parameter) 
fiducial_maps = {}
for hierarchy in ['NMH','IMH']:
  fiducial_params = select_hierarchy(params,normal_hierarchy=(hierarchy=='NMH'))
  fiducial_maps[hierarchy] = template_maker.get_template(get_values(fiducial_params))

# Get_gradients and get_hierarchy_gradients will both (temporarily) 
# store the templates used to generate the gradient maps
store_dir = args.outdir if args.save_templates else tempfile.gettempdir()

# Calculate Fisher matrices for the user-defined cases (NHM true and/or IMH true)
for data_tag, data_normal in chosen_data:

  logging.info("Running analysis for %s."%(data_tag.split('_')[1]))

  # The fiducial params are selected from the hierarchy case that does NOT match
  # the data, as we are varying from this model to find the 'best fit' 
  fiducial_params = select_hierarchy(params,not data_normal)

  # Get the free parameters (i.e. those for which the gradients should be calculated)
  free_params = select_hierarchy(get_free_params(params),not data_normal)
  gradient_maps = {}
  for param in free_params.keys():
    
    if param=='hierarchy':
      gradient_maps[param] = get_hierarchy_gradients(data_tag.split('_')[1],
						     fiducial_maps,
						     fiducial_params,
						     grid_settings,
						     store_dir,
						     )	
  
    else:
      gradient_maps[param] = get_gradients(data_tag.split('_')[1],
					   param,
                                           template_maker,
                                           fiducial_params,
                                           grid_settings,
                                           store_dir)
  

  logging.info("Building Fisher matrix for %s."%(data_tag.split('_')[1]))
    
  fisher[data_tag] = build_fisher_matrix(gradient_maps,fiducial_maps['IMH'] if data_normal else fiducial_maps['NMH'],fiducial_params)
  
  for chan in fisher[data_tag]:
    logging.info("Writing Fisher matrix for channel %s to %s"%(chan,os.path.join(args.outdir,'fisher_data_%s_%s.json'%(data_tag.split('_')[1],chan))))
    fisher[data_tag][chan].saveFile(os.path.join(args.outdir,'fisher_data_%s_%s.json'%(data_tag.split('_')[1],chan)))
	
#for channel in fisher[data_tag]:
    # add labels if needed, priors are already there

"""
# Add Fisher matrices
for data_tag in fisher:
    fisher[data_tag][''] = sum(fisher[data_tag][chan]['matrix'] for chan in fisher[data_tag])
    logging.info("Writing complete Fisher matrix for %s to %s"%(data_tag.split('_')[1],os.path.join(store_dir,'fisher_data_%s.json'%(data_tag.split('_')[1]))))
    fisher[data_tag][''].saveFile(os.path.join(store_dir,'fisher_data_%s.json'%data_tag.split('_')[1]))
"""
#Outfile: fisher,
#         fiducial_templates (NH, IH),
#         templates?
#
#fisher = {'tracks' : type<FisherMatrix>,
#    'cascades': type<FisherMatrix>,
#    '': type<FisherMatrix>}
