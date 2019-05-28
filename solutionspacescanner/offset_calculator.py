import numpy as np
import os
import errno
import argparse

## ABOUT:
##
## offset_calculator provides a set of functions used by rewire_fos, but can also be used seperately
## for other calculations
##


################################################################################################
####                                                                                        ####
####                      Global parameters                                                 ####
####                                                                                        ####
################################################################################################

AAs = ['A','C','D','E','F','G','H','I','K','L','M','N','P','Q','R','S','T','V','W','Y']

AA2INT = {'A':0, 'C':1, 'D':2,'E':3,'F':4,'G':5,'H':6,'I':7,'K':8,'L':9,'M':10,'N':11,'P':12,'Q':13,'R':14,'S':15,'T':16,'V':17,'W':18,'Y':19}
INT2AA = {0:'A', 1:'C', 2:'D', 3:'E', 4:'F', 5:'G', 6:'H', 7:'I', 8:'K', 9:'L', 10:'M', 11:'N', 12:'P', 13:'Q', 14:'R', 15:'S', 16:'T', 17:'V', 18:'W', 19:'Y'}

# MAX SASA for sidechain and backbone in each residue, as measured from 
# ACE-XX-NME dipeptide
SASA_MAX = np.array([[7.581871795654296875e+01, 7.607605743408203125e+01],
                     [1.154064483642578125e+02, 6.787722015380859375e+01],
                     [1.302558288574218750e+02, 7.182710266113281250e+01],
                     [1.617985687255859375e+02, 6.805746459960937500e+01],
                     [2.093871002197265625e+02, 6.598278808593750000e+01],
                     [0.000000000000000000e+00, 1.149752731323242188e+02],
                     [1.808149414062500000e+02, 6.750666809082031250e+01],
                     [1.727196502685546875e+02, 6.034464645385742188e+01],
                     [2.058575897216796875e+02, 6.871156311035156250e+01],
                     [1.720360412597656250e+02, 6.451246643066406250e+01],
                     [1.847660064697265625e+02, 6.778076934814453125e+01],
                     [1.427441253662109375e+02, 6.680493164062500000e+01],
                     [1.342914733886718750e+02, 5.583909606933593750e+01],
                     [1.733262939453125000e+02, 6.660184478759765625e+01],
                     [2.364875640869140625e+02, 6.673487854003906250e+01],
                     [9.587133026123046875e+01, 7.287202453613281250e+01],
                     [1.309214324951171875e+02, 6.421310424804687500e+01],
                     [1.431178131103515625e+02, 6.172962188720703125e+01],
                     [2.545694122314453125e+02, 6.430991363525390625e+01],
                     [2.225183105468750000e+02, 7.186695098876953125e+01]])

# baseline sidechain FOS values as taken from the ABINSTH implicit solvent model. Note
# the FOS of G is set to 0 here (no sidechain).
FOS_baseline   = {'A':1.9, 
                  'C':-1.2, 
                  'D':-107.3,
                  'E':-107.3, 
                  'F':-0.8, 
                  'G': 0,
                  'H':-10.3,
                  'I':2.2, 
                  'K':-100.9, 
                  'L':2.3, 
                  'M':-1.4, 
                  'N':-9.7, 
                  'P':2.0,  
                  'Q':-9.4, 
                  'R':-100.9,   
                  'S':-5.1,  
                  'T':-5.0, 
                  'V':2.0, 
                  'W':-5.9,
                  'Y':-6.1}

# backbone baseline FOS, as taken from the ABSINTH implicit solvent model
backbone_baseline = -10.1


## ...........................................................................
##
def sanitize_sequence(s):
    """
    Function that parses protein string (one-letter amino acid sequence) and verifies each residue 
    can be correctly dealt with

    """

    seq = s.upper()
    for a in seq:
        if a not in AAs:
            raise Exception('---- Found invalid amino acid (%s)'%(a))

    return seq

## ...........................................................................
##
def get_overal_group_SASA(resvector, group):
    """
    Returns the max possible SASA associated with one or more amino acids as defined by
    the 'group' string. Note 'B' in group means backbone.

    This function isn't ACTUALLY used for the main FOS calculation but I kept it because it may be useful.

    """
    total = 0.0

    for AA in group:

        # if backbone is the group...
        if group == 'B':
            total = 0
            for AA_IDX in range(0,20):

                # increment total by number of residue of type A * max possible available backbone associated with
                # that residue type (SASA_MAX[AA_IDX][1] -> 1 means backbone
                total = total + resvector[AA_IDX]*SASA_MAX[AA_IDX][1]

        else:
            AA_IDX = AA2INT[AA]

            # increment total by number of residue of type A * max possible available backbone associated with
            # that residue type (SASA_MAX[AA_IDX][0] -> 0 means sidechain
            total = total + resvector[AA_IDX]*SASA_MAX[AA_IDX][0]
        
    return total


def print_sanity_checks(resvector,seq, offset_vector):

    print("Running offset_calculator....")
    print("")
    print("Seq: %s" %  seq)
    print("Offsets: %s" % (str(offset_vector)))
    print("")
    max_fos = 0
    for AA in AAs:
        
        AA_IDX=AA2INT[AA]

        BB_corection_factor = (SASA_MAX[AA_IDX][1]/SASA_MAX[5][1]) # BB correction for presence of sidechain
        print("Residue %s total GTFE = %3.6f" % (AA, FOS_baseline[INT2AA[AA_IDX]] + backbone_baseline*BB_corection_factor))
        max_fos = max_fos + resvector[AA_IDX]*FOS_baseline[INT2AA[AA_IDX]] + resvector[AA_IDX]*backbone_baseline*BB_corection_factor

    print("")
    print("Total MTFE: %5.5f kcal/mol" % max_fos)
    print("")

        


## ...........................................................................
##
def get_group_specific_FOS(resvector, group, offset):
    """
    Group should be a string of residues

    """
    max_fos = 0.0

    # for each sidechain
    for AA in AAs:
        
        AA_IDX=AA2INT[AA]
        
        # if sidechain group is being changed
        if AA in group:

            # sidechain max possible FOS with offset set
            max_fos = max_fos + resvector[AA_IDX]*(FOS_baseline[INT2AA[AA_IDX]]+offset);
        else:

            # sidechain max possible FOS (no offset)
            max_fos = max_fos + resvector[AA_IDX]*FOS_baseline[INT2AA[AA_IDX]];

        # if backbone not going to be changed then deal with this here
        if 'B' not in group:

            # and backbone max possible FOS (no offset) with fractional correction cos sidechains take up space!
            BB_corection_factor = (SASA_MAX[AA_IDX][1]/SASA_MAX[5][1]) # BB correction for presence of sidechain
            max_fos = max_fos + resvector[AA_IDX]*backbone_baseline*BB_corection_factor



    # if backbone is being corrected then we DID NOT include it in the previous loop and we deal woth it here..
    if 'B' in group:

        for AA in AAs:        
            AA_IDX=AA2INT[AA]
        
            # sidechains have already been dealt with so if 'B' was in group we are now JUST adjusting the backbone

            # and backbone max possible FOS (no offset)
            BB_corection_factor = (SASA_MAX[AA_IDX][1]/SASA_MAX[5][1]) # BB correction for presence of sidechain
            max_fos = max_fos + resvector[AA_IDX]*(backbone_baseline+offset)*BB_corection_factor
    
    return max_fos


## ...........................................................................
##
def build_resvector(s):
    """
    Function that returns a 20-place array with the counts for each residue type
    """

    return_vector = [] 
    for A in AAs:
        return_vector.append(s.count(A))

    return return_vector



## ...........................................................................
##
def run_normalization(seq, AA_groups, FOS_offset_vector, prefix=None, percent=False):

    seq = sanitize_sequence(seq)
    resvector = build_resvector(seq)

    return_matrix=[]

    print_sanity_checks(resvector,seq, FOS_offset_vector)
    
    for group in AA_groups:
        gvector=[]
        for offset in FOS_offset_vector:
            gvector.append(get_group_specific_FOS(resvector, group, offset))
        return_matrix.append(gvector)

    if prefix:        
        np.savetxt('%s_MTFE_values.csv' % (prefix), np.array(return_matrix).transpose(),delimiter=', ')
        np.savetxt('%s_MTFE_values_used.csv' % (prefix), FOS_offset_vector, delimiter=', ')
    else:
        np.savetxt('MTFE_values.csv', np.array(return_matrix).transpose(),delimiter=', ')
        np.savetxt('MTFE_values_used.csv', FOS_offset_vector, delimiter=', ')



## ...........................................................................
##
def run_normalization_with_percent(seq, AA_groups, FOS_percent_vector, prefix=None):
    """
    Note that for every group a % is the same, but we just create this redundant 
    output file so both types of analysis scripts work on the same input
    
    """

    seq = sanitize_sequence(seq)
    resvector = build_resvector(seq)

    return_matrix=[]

    print_sanity_checks(resvector,seq, FOS_percent_vector)

    # first calculate value without any percentage changes
    local_wt_MTFE = get_group_specific_FOS(resvector, 'B', 0)
    
    # compute the offset vector first
    FOS_offset_vector = []
    for pcnt in FOS_percent_vector:
            offset_fos = abs(local_wt_MTFE)*(abs(pcnt)/100.0)            
            if pcnt < 0:
                FOS_offset_vector.append(+offset_fos)
            else:
                FOS_offset_vector.append(-offset_fos)


            

    
    for group in AA_groups:

        gvector=[]

        for FO in FOS_offset_vector:
            gvector.append(local_wt_MTFE+FO)

        return_matrix.append(gvector)

    if prefix:        
        np.savetxt('%s_MTFE_values.csv' % (prefix), np.array(return_matrix).transpose(),delimiter=', ')
        np.savetxt('%s_MTFE_values_used.csv' % (prefix), FOS_offset_vector, delimiter=', ')
    else:
        np.savetxt('MTFE_values.csv', np.array(return_matrix).transpose(),delimiter=', ')
        np.savetxt('MTFE_values_used.csv', FOS_offset_vector, delimiter=', ')


## ...........................................................................
##
def get_delta_percentage_MTFEs(seq, percentage, AAgroup):

    if percentage < 0 or percentage > 100:
        Exception("Percentage must be between 0 and 100")


    if percentage == 0:
        print("No offset required (target percentage change = 0)")
        return 0

    print("Input percentage: %3.3f " % percentage)
    seq = sanitize_sequence(seq)
    resvector = build_resvector(seq)

    wt_MTFE = get_group_specific_FOS(resvector, AAgroup, 0)
    MTFE_resolution = 0.005

    trajectory=[]
    offset = -MTFE_resolution


    if percentage < 0:
        PC = -1
    else:
        PC = 1
    percentage=abs(percentage)

    delta_percentaget_MTFE = 100*((get_group_specific_FOS(resvector, AAgroup, offset) - wt_MTFE)/wt_MTFE)

    while delta_percentaget_MTFE < percentage:
        offset=offset-MTFE_resolution
        delta_percentaget_MTFE = 100*((get_group_specific_FOS(resvector, AAgroup, offset)-wt_MTFE)/wt_MTFE)
        trajectory.append(delta_percentaget_MTFE)

    # check which of the two values that straddle the boundary is closed and choose the best of the two
    
    if abs(trajectory[-2]-percentage) < abs(delta_percentaget_MTFE-percentage):
        offset=offset-MTFE_resolution
        delta_percentaget_MTFE = trajectory[-2]


    # if we have a negative we are reducing the RFOS 
    if PC < 0:
        offset=-offset
        delta_percentaget_MTFE=-delta_percentaget_MTFE

    print("Offset of %4.2f to groups [%s] gives a delta MTFE percent of %2.2f (original = %5.1f kcal/mol, rewired = %5.1f kcal/mol) " %(offset, AAgroup, delta_percentaget_MTFE, wt_MTFE, get_group_specific_FOS(resvector, AAgroup, offset)))

    return offset

