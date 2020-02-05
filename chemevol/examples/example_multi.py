'''
Example of using ChemEvol without using the BulkEvolve class, but with multiple galaxies.

---------------------------------------------------
First set up initial parameters for galaxy model by editing the dictionary
initial_galaxy_params

- name: 				someway to identify your galaxy
- gasmass_init: 		initial gas mass in solar masses
- starmass_init: 		initial stellar mass in solar masses
- dustmass_init: 		initial dust mass in solar masses
- Z_init: 				initial metallicity in solar masses
- SFH: 					filename for star formation history file (filename.sfh)
						if you don't specify a file, it will default to MW like SFH
- add_bursts:			if you are using a .sfe file, you can add bursts following De Vis et al 2020						
- t_end:				end of time array for the model
- t_start:				start of time array for the model
- gamma: 				power law for extrapolation of SFH if using SFH generated by MAGPHYS code, otherwise set to zero
- IMF_fn:          		choice of IMF function: Chab/chab/c, TopChab/topchab/tc,
		  				Kroup/kroup/k or Salp/salp/s
- dust_source: 			choice of dust sources to be included:
						SN: supernova dust only
						LIMS: low intermediate mass stars dust only
						LIMS+SN: both SN and LIMS included
						ALL: includes supernovae, LIMS and grain growth combined
- cold_gas_fraction:	Fraction of the gas that is in cold dense clouds, default is 0.5 eg Asano et al 2013
- use_THEMIS:			If set to True, use the THEMIS dust production and destruction mechanisms					
- delta_lims_fresh: 	Efficiency of fresh metals condensing into dust grains in LIMS (1<M_i<8Msun)
						Set to 0.15-0.4 in Morgan & Edmunds (2003); 0.15 in De Vis et al 2017b in press
- reduce_sn_dust		reduce the contribution from SN dust (currently set to values from
						Todini & Ferrera 2001).  Can be True or False. To reduce dust mass
						then quote number to reduce by (factor).
- destroy: 				on: add dust destruction from SN shocks: True or False
						mass: Amount of material destroyed by each SN
						(typically 1000 or 100Msun)
- fragmentgrains:		THEMIS photofragmentation rate of large a-C:H/a-C grains
- effective_snrate_factor: 	factor that the sn_rate needs to be corrected by to account for previous SN clearing dust in the vicinity of this SN, default is 0.36.
- graingrowth = 		grain growth parameter from THEMIS (clouds) or Mattsson & Andersen 2012 (depending on whether use_THEMIS is True).
- graingrowth2 = 		grain growth parameter from THEMIS (diffuse ISM)
- inflows: 				there are five parameters
							on: do you wish to turn inflows on: input True or False
							mass: 	If 0, keep the masses defined in sfh file. 
									If >0, set up the inflows so that `mass' gives the total amount of inflowing material
							inflows_metals = metallicity of inflow Y or N: input a number appropriate for primordial inflow gas eg 1e-3 to 1e-4 (Rubin et al 2012, Peng & Maiolino 2013).
							inflows_xSFR = inflow rate of gas is X * SFR: input a number X; this parameter is not used in the current version, but can easily be reintroduced using the inflows_SFR function in functions.py
							inflows_dust = amount of dust inflow: input a number appropriate for dust eg 0.4 x the metallicity (Edmunds 2000)
- outflows: 			there are four parameters: Outflow rates are taken from Nelson et al (2019)
							on: do you wish to turn outflows on Y or N: input True or False
 							outflows_metals = metallicity of inflow: input True or False
						   	(True = metallicity of system, False = 0)
						 	outflows_dust = amount of dust in outflow: input True of False
							(True = dust/gas of system, False = 0)
							reduce = reduces the outflow rates from Nelson et al (2019) by this factor
- recycle: 				there are three parameters: 
							on: do you wish to turn outflow recycling on Y or N: input True or False
							esc_prob_perGyr: probability per Gyr that the outflowing material is lost to the IGM before it is recycled
							reaccr_time_factor: scale the recycling time up or down by this factor
- available_metal_fraction:	fraction of metals that is available for grain growth in the diffuse ISM, 
							this is effectively the maximum dust-to-metal ratio in the diffuse ISM.
							This is also used to calculate the maximum dust-to-metal ratio in clouds as 2.45 times the available_metal_fraction.
- SNyield:				String identifier to choose which SN metal yield table is used (see lookups.py)			
- AGByield:				String identifier to choose which SN metal yield table is used (see lookups.py)				
- totyields:			Boolean deciding whether total metal yields or fresh metal yields should ne used				
- isotopes:				Isotopes/metal budgets to be tracked throughout the model. These have to be consistent with the SNyields and AGByields tables (see lookups.py)			
- Pristine_isotope_fractions:	If there are metals in the inflows, Pristine_isotope_fractions decides how much of which metals are present.


Each run will be used to generate the evolution of dust, gas,
SFR, metals and stars over time
---------------------------------------------------------------------------
'''

from chemevol import ChemModel
from astropy.io import ascii


# initialise your galaxy parameters here and choice of models
# each {} entry is per galaxy separated by comma in list

inits = [
			{	'name': 'Model_1',
				'gasmass_init': 1e8,
				'starmass_init': 0,
				'dustmass_init': 0,
				'Z_init': 0.0,
				'SFH': 'average.sfe',
				'add_bursts': False,
				't_end': 13.8,
				't_start': 0.0,
				'gamma': 0,
				'IMF_fn': 'Chab',
				'dust_source': 'ALL',
				'cold_gas_fraction': 0.5,
				'use_THEMIS': True,
				'delta_lims_fresh': 0.15,
				'reduce_sn_dust': {'on': True, 'factor': 5},
				'destroy': {'on': True, 'mass': 10},
				'fragmentgrains': {'on': True, 'tau': 0.5},
				'effective_snrate_factor': 0.36,
				'graingrowth': 2000,
				'graingrowth2': 1,
				'inflows':{'on': True, 'mass':0, 'metals': 0., 'xSFR': 1, 'dust': 0},
				'outflows':{'on': True, 'metals': True, 'dust': True, 'reduce': 1.},
				'recycle':{'on': True, 'esc_prob_perGyr':0.2, 'reaccr_time_factor': 0.5},
				'available_metal_fraction': 0.3,
				'SNyield': "LC18_R300", 
				'AGByield': "KA18_low",
				'totyields': True,
				'isotopes':["Z","O","N"],
				'Pristine_isotope_fractions': [1.,0.435, 0.055]},	
				
			{	'name': 'Model_2',
				'gasmass_init': 1e8,
				'starmass_init': 0,
				'dustmass_init': 0,
				'Z_init': 0.0,
				'SFH': 'average.sfe',
				'add_bursts': False,
				't_end': 13.8,
				't_start': 0.0,
				'gamma': 0,
				'IMF_fn': 'Chab',
				'dust_source': 'ALL',
				'cold_gas_fraction': 0.5,
				'use_THEMIS': True,
				'delta_lims_fresh': 0.15,
				'reduce_sn_dust': {'on': True, 'factor': 10},
				'destroy': {'on': True, 'mass': 10},
				'fragmentgrains': {'on': True, 'tau': 0.5},
				'effective_snrate_factor': 0.36,
				'graingrowth': 4000,
				'graingrowth2': 1,
				'inflows':{'on': True, 'mass':0, 'metals': 0., 'xSFR': 1, 'dust': 0},
				'outflows':{'on': True, 'metals': True, 'dust': True, 'reduce': 1.},
				'recycle':{'on': True, 'esc_prob_perGyr':0.2, 'reaccr_time_factor': 0.5},
				'available_metal_fraction': 0.5,
				'SNyield': "LC18_R300", 
				'AGByield': "KA18_low",
				'totyields': True,
				'isotopes':["Z","O","N"],
				'Pristine_isotope_fractions': [1.,0.435, 0.055]},		

			{	'name': 'Model_3',
				'gasmass_init': 1e8,
				'starmass_init': 0,
				'dustmass_init': 0,
				'Z_init': 0.0,
				'SFH': 'average.sfe',
				'add_bursts': False,
				't_end': 13.8,
				't_start': 0.0,
				'gamma': 0,
				'IMF_fn': 'Chab',
				'dust_source': 'ALL',
				'cold_gas_fraction': 0.5,
				'use_THEMIS': True,
				'delta_lims_fresh': 0.15,
				'reduce_sn_dust': {'on': True, 'factor': 20},
				'destroy': {'on': True, 'mass': 10},
				'fragmentgrains': {'on': True, 'tau': 0.5},
				'effective_snrate_factor': 0.36,
				'graingrowth': 8000,
				'graingrowth2': 1,
				'inflows':{'on': True, 'mass':0, 'metals': 0., 'xSFR': 1, 'dust': 0},
				'outflows':{'on': True, 'metals': True, 'dust': True, 'reduce': 1.},
				'recycle':{'on': True, 'esc_prob_perGyr':0.2, 'reaccr_time_factor': 0.5},
				'available_metal_fraction': 0.3,
				'SNyield': "LC18_R300", 
				'AGByield': "KA18_low",
				'totyields': True,
				'isotopes':["Z","O","N"],
				'Pristine_isotope_fractions': [1.,0.435, 0.055]},

			{	'name': 'Model_4',
				'gasmass_init': 1e10,
				'starmass_init': 0,
				'dustmass_init': 0,
				'Z_init': 0.0,
				'SFH': 'average.sfe',
				'add_bursts': False,
				't_end': 13.8,
				't_start': 0.0,
				'gamma': 0,
				'IMF_fn': 'Chab',
				'dust_source': 'ALL',
				'cold_gas_fraction': 0.5,
				'use_THEMIS': True,
				'delta_lims_fresh': 0.15,
				'reduce_sn_dust': {'on': True, 'factor': 5},
				'destroy': {'on': True, 'mass': 10},
				'fragmentgrains': {'on': True, 'tau': 0.5},
				'effective_snrate_factor': 0.36,
				'graingrowth': 2000,
				'graingrowth2': 1,
				'inflows':{'on': True, 'mass':0, 'metals': 0., 'xSFR': 1, 'dust': 0},
				'outflows':{'on': True, 'metals': True, 'dust': True, 'reduce': 1.},
				'recycle':{'on': True, 'esc_prob_perGyr':0.2, 'reaccr_time_factor': 0.5},
				'available_metal_fraction': 0.3,
				'SNyield': "LC18_R300", 
				'AGByield': "KA18_low",
				'totyields': True,
				'isotopes':["Z","O","N"],
				'Pristine_isotope_fractions': [1.,0.435, 0.055]},	
				
			{	'name': 'Model_5',
				'gasmass_init': 1e10,
				'starmass_init': 0,
				'dustmass_init': 0,
				'Z_init': 0.0,
				'SFH': 'average.sfe',
				'add_bursts': False,
				't_end': 13.8,
				't_start': 0.0,
				'gamma': 0,
				'IMF_fn': 'Chab',
				'dust_source': 'ALL',
				'cold_gas_fraction': 0.5,
				'use_THEMIS': True,
				'delta_lims_fresh': 0.15,
				'reduce_sn_dust': {'on': True, 'factor': 10},
				'destroy': {'on': True, 'mass': 10},
				'fragmentgrains': {'on': True, 'tau': 0.5},
				'effective_snrate_factor': 0.36,
				'graingrowth': 4000,
				'graingrowth2': 1,
				'inflows':{'on': True, 'mass':0, 'metals': 0., 'xSFR': 1, 'dust': 0},
				'outflows':{'on': True, 'metals': True, 'dust': True, 'reduce': 1.},
				'recycle':{'on': True, 'esc_prob_perGyr':0.2, 'reaccr_time_factor': 0.5},
				'available_metal_fraction': 0.5,
				'SNyield': "LC18_R300", 
				'AGByield': "KA18_low",
				'totyields': True,
				'isotopes':["Z","O","N"],
				'Pristine_isotope_fractions': [1.,0.435, 0.055]},		

			{	'name': 'Model_6',
				'gasmass_init': 1e10,
				'starmass_init': 0,
				'dustmass_init': 0,
				'Z_init': 0.0,
				'SFH': 'average.sfe',
				'add_bursts': False,
				't_end': 13.8,
				't_start': 0.0,
				'gamma': 0,
				'IMF_fn': 'Chab',
				'dust_source': 'ALL',
				'cold_gas_fraction': 0.5,
				'use_THEMIS': True,
				'delta_lims_fresh': 0.15,
				'reduce_sn_dust': {'on': True, 'factor': 20},
				'destroy': {'on': True, 'mass': 10},
				'fragmentgrains': {'on': True, 'tau': 0.5},
				'effective_snrate_factor': 0.36,
				'graingrowth': 8000,
				'graingrowth2': 1,
				'inflows':{'on': True, 'mass':0, 'metals': 0., 'xSFR': 1, 'dust': 0},
				'outflows':{'on': True, 'metals': True, 'dust': True, 'reduce': 1.},
				'recycle':{'on': True, 'esc_prob_perGyr':0.2, 'reaccr_time_factor': 0.5},
				'available_metal_fraction': 0.3,
				'SNyield': "LC18_R300", 
				'AGByield': "KA18_low",
				'totyields': True,
				'isotopes':["Z","O","N"],
				'Pristine_isotope_fractions': [1.,0.435, 0.055]},
		]


snrate = []
all_results = []
galaxies = []

for item in inits:
	ch = ChemModel(**item)

	'''
	call modules to run the model:
	    snrate:         SN rate at each time step - this also sets time array
	                    so ch.supernova_rate() must be called first to set
	                    time array for the entire code

	    all results:    contains all relevant chemical evolution parameters to be outputted
	'''
	snrate = ch.supernova_rate()
	all_results = ch.gas_metal_dust_mass(snrate)

	# write all the results to a dictionary
	params = {'time' : all_results[:,0],
	       'z' : all_results[:,1],
	       'mgas' : all_results[:,2],
	       'mstars' : all_results[:,3],
	       'metallicity' : all_results[:,4],
	       'mdust' : all_results[:,5],
	       'dust_metals_ratio' : all_results[:,6],
	       'sfr' : all_results[:,7],
	       'dust_all' : all_results[:,8],
	       'dust_stars' : all_results[:,9],
	       'dust_ism' : all_results[:,10],
	       'time_destroy' : all_results[:,11],
	       'time_fragment' : all_results[:,12],
	       'time_gg_diffuse' : all_results[:,13],
	       'time_gg_cloud' : all_results[:,14],
	       'mgas_outflow' : all_results[:,15],
	       'mgas_recycled' : all_results[:,16],
	       'mgas_inflow' : all_results[:,17],
	       'mgas_IGM' : all_results[:,18],
	       'mdust_IGM' : all_results[:,19],
	       'mdust_diffuse' : all_results[:,20],
	       'mdust_cloud' : all_results[:,21]}

	#compute additional parameters
	params['fg'] = params['mgas']/(params['mgas']+params['mstars'])
	params['ssfr'] = params['sfr']/params['mstars']

	paramsorder=['time','z','fg','mgas','mstars','mdust','mdust_diffuse',\
	            'mdust_cloud','metallicity','dust_metals_ratio','sfr',\
	            'ssfr','dust_all','dust_stars','dust_ism','time_destroy',\
	            'time_fragment','time_gg_diffuse','time_gg_cloud','mgas_outflow',\
	            'mgas_recycled','mgas_inflow','mgas_IGM','mdust_IGM']
	            
	#properties for the isotypes specified in input
	for iso,nameiso in enumerate(item['isotopes']):
	    Miso=all_results[:,22+iso]
	    params['M'+nameiso]=Miso
	    Miso_IGM=all_results[:,22+iso+len(item['isotopes'])]
	    params['M'+nameiso+'_IGM']=Miso_IGM
	    paramsorder+=['M'+nameiso,'M'+nameiso+'_IGM']

	# write out to file based on 'name' identifier
	name = item['name']

	#ascii.write(params,str(name+'.dat'),names=paramsorder)
	ascii.write(params,str(name+'.csv'),format='csv',names=paramsorder) # .csv option

	# if you want an array including every inits entry:
	galaxies.append(params)
