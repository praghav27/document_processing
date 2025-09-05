metadata = {'project_name': 'Not mentioned in document', 'client': 'Hydro One Networks Inc.', 'region': 'Chatham/Lakeshore', 'industry': 'Power & Energy', 'prepared_date': 'Not mentioned in document', 'station_discipline': 'ELE', 'scope_of_work': 'The scope includes electrical installation works such as erection of insulators, alignment of steel structures, installation of mechanical linkage, functional testing, interlocking checks, grounding, lighting systems, cable trenches, and conduits. It also involves installation of major equipment like transformers, circuit breakers, disconnect switches, surge arresters, and telecommunication systems.', 'required_activities': 'The required activities include installation, alignment, adjustment, and testing of electrical equipment such as transformers, circuit breakers, disconnect switches, surge arresters, and telecommunication systems. Grounding connections, lighting systems, cable trenches, and conduits must be installed as per design specifications. Site testing and inspection of equipment for damage, alignment, and functionality are mandatory.'}

section_name = "scope of work"

exclude_keys = {"scope_of_work", "required_activities"}
 
# Convert JSON key-value pairs into a sentence excluding chosen keys
metadata_str = "; ".join([f"{k} is {v}" for k, v in metadata.items() if k not in exclude_keys])
 
# Combine with base string
final_sentence = f"{section_name} Metadata -> {metadata_str}."

print(final_sentence)

print(metadata['scope_of_work'])
print(metadata['required_activities'])