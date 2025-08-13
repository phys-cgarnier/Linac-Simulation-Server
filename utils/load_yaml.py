import yaml

def load_relevant_controls(yaml_file):
    with open(yaml_file, 'r') as file:
        data = yaml.safe_load(file)  
    relevant_controls = {}  
    # Process magnets
    for name, info in data.get('magnets', {}).items():
        if info['metadata']['type'] == 'QUAD':
            control_name = info['controls_information']['control_name']
            relevant_controls[control_name] = {}
            relevant_controls[control_name]['pvs'] = info['controls_information']['PVs']
            relevant_controls[control_name]['metadata'] = info['metadata']
            relevant_controls[control_name]['madname'] = name.lower() 
    # Process screens
    for name, info in data.get('screens', {}).items():
        if info['metadata']['type'] == 'PROF':  # Assuming 'PROF' represents OTR
            control_name = info['controls_information']['control_name']
            relevant_controls[control_name] = {}
            relevant_controls[control_name]['pvs'] = info['controls_information']['PVs']
            relevant_controls[control_name]['metadata'] = info['metadata']
            relevant_controls[control_name]['madname'] = name.lower()
    
    # Process tcav
    for name, info in data.get('tcavs', {}).items():
        if info['metadata']['type'] == 'LCAV':
            control_name = info['controls_information']['control_name']
            relevant_controls[control_name] = {}
            relevant_controls[control_name]['pvs'] = info['controls_information']['PVs']
            relevant_controls[control_name]['metadata'] = info['metadata']
            relevant_controls[control_name]['madname'] = name.lower() 

    for name, info in data.get('bpms', {}).items():
        if info['metadata']['type'] == 'BPM':
            control_name = info['controls_information']['control_name']
            relevant_controls[control_name] = {}
            relevant_controls[control_name]['pvs'] = info['controls_information']['PVs']
            relevant_controls[control_name]['metadata'] = info['metadata']
            relevant_controls[control_name]['madname'] = name.lower() 
    return relevant_controls

#TODO: multiarea