'''
Chemevol - Python package to read in a star formation history file,
input galaxy parameters and run a chemical evolution model to determine the evolution
of gas, metals and dust in galaxies.

Running this script will produce
(a) a results data file
(b) a pop-up plot for looking at gas, dust and metal evolution

The code is based on Morgan & Edmunds 2003 (MNRAS, 343, 427)
and described in detail in Rowlands et al 2014 (MNRAS, 441, 1040).

If you use this code, please do cite the above papers.

Copyright (C) 2015 Haley Gomez and Edward Gomez, Cardiff University and LCOGT
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
'''
import functions as f
from evolve import ChemModel
import data as d
import matplotlib.pyplot as plt

'''------------------------------------------------------------------------
First set up initial parameters for galaxy model by editing the dictionary
initial_galaxy_params

- gasmass_init: 		initial gas mass in solar masses
- SFH: 					filename for star formation history file (filename.sfh)
						if you don't specify a file, it will default to MW like SFH
- t_end:				end of time array for chemical integrals
- gamma: 				power law for extrapolation of SFH
						if using SFH generated by MAGPHYS code
- IMF_fn:          		choice of IMF function: Chab/chab/c, TopChab/topchab/tc,
		  				Kroup/kroup/k or Salp/salp/s
- dust_source: 			choice of dust sources to be included:
						SN: supernova dust only
						LIMS: low intermediate mass stars dust only
						LIMS+SN: both SN and LIMS included
						ALL: includes supernovae, LIMS and grain growth combined
- reduce_sn_dust		reduce the contribution from SN dust (currently set to values from
						Todini & Ferrera 2001).  If leave default specify False. To reduce dust mass
						then quote number to reduce by
- destroy: 				add dust destruction from SN shocks: True or False
- inflows: 				there are two parameters
 						metals = metallicity of inflow: input a number
								 xSFR = inflow rate is X * SFR: input a number
								 dust = amount of dust inflow: input a number
- outflows: 			there are two parameters
 						metals = metallicity of inflow: input True or False
						True = metallicity of system, False = 0
								 xSFR = inflow rate is X * SFR: input a number
								 dust = amount of dust in outflow: input True of False
							  	 		True = dust/gas of system, False = 0
- cold_gas_fraction = 	fraction of gas in cold dense state for grain growth
					  	typically 0.5-0.9 for high z systems, default is 0.5
- epsilon_grain = 		grain growth parameter from Mattsson & Andersen 2012
						default is 500 for t_grow ~ 10Myr.
- destruct = 			amount of material destroyed by each SN (typically 1000 or 100Msun)


Each run will be used to generate the evolution of dust, gas,
SFR, metals and stars over time
---------------------------------------------------------------------------
'''

init_keys = (['gasmass_init','SFH','t_end','inflows','outflows','dust_source','destroy',\
			'IMF_fn','gamma','epsilon_grain','destruct'])

'''
THIS WILL BE EDITED TO DO MORE THAN ONE RUN
initial_galaxy_params = {'run1': {
							'gasmass_init': 4.8e10,
							'SFH': 'MilkyWay.sfh',
							't_end': 20.,
							'gamma': 0,
							'IMF_fn': 'Chab',
							'dust_source': 'ALL',
							'reduce_sn_dust': False,
							'destroy':True,
							'inflows':{'metals': 0., 'xSFR': 0, 'dust': True},
							'outflows':{'metals': True, 'xSFR': 0, 'dust': False},
							'cold_gas_fraction': 0.5,
							'epsilon_grain': 500.,
							'destruct': 1000.
							},
						'run2': {
							'gasmass_init':4e10,
							'SFH':'MilkyWay.sfh',
							't_end': 25.,
							'gamma':0,
							'IMF_fn':'c',
							'dust_source':'LIMS+SN',
							'reduce_sn_dust': False
							'destroy':True,
							'inflows':{'metals': 1e-4, 'xSFR': 0, 'dust': 0},
							'outflows':{'metals': False, 'xSFR': 0, 'dust': False},
							'cold_gas_fraction':0.,
							'epsilon_grain': 1e5,
							'destruct': 100.
							}
							}

#Now we will test that the input parameters are A-OK:
#f.validate_initial_dict(init_keys, initial_galaxy_params)
'''

inits = {
        		'gasmass_init': 4e10,
				'SFH': 'delayed.sfh',
        		't_end': 20.,
				'gamma': 0,
				'IMF_fn': 'Chab',
				'dust_source': 'LIMS+SN',
				'reduce_sn_dust': False,
				'destroy': False,
				'inflows':{'metals': 0., 'xSFR': 0, 'dust': 0},
				'outflows':{'metals': True, 'xSFR': 0, 'dust': True},
				'cold_gas_fraction': 0.5,
				'epsilon_grain': 1000.,
        		'destruct': 1000.
              }

ch = ChemModel(**inits)

# call modules to run the model

# SN rate at each time step - this also sets time array so
# this must be run before ch.gas_metal_dust_mass
snrate = ch.supernova_rate()

# returns
# (a) dust sources vs time (all, stars only and grain growth only)
# (b) timescales for destruction & grain growth in Gyrs
# (c) all results -- t, mg, m*, mz, Z, md, md/mz, sfr
dust_sources, timescales, all_results = ch.gas_metal_dust_mass(snrate)

time = all_results[:,0]
mgas = all_results[:,1]
mstars = all_results[:,2]
metalmass = all_results[:,3]
metallicity = all_results[:,4]
mdust = all_results[:,5]
dust_metals = all_results[:,6]
sfr = all_results[:,7]
t_graingrow = timescales[:,1]
t_destroy = timescales[:,0]

# create gasfraction and ssfr parameters
gasfraction = mgas/(mgas+mstars)
print gasfraction
ssfr = sfr/mstars

#write to a file
d.writedata(time, mgas, mstars, sfr, ssfr, mdust, metalmass, metallicity, gasfraction)

# make some quick look up plots
d.figure(time,mgas,mstars,metalmass,metallicity,mdust,dust_metals,gasfraction,dust_sources,timescales)
