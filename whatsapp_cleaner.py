import re
import pandas as pd
from datetime import datetime

def clean_whatsapp_log(input_file_path):
    """
    Cleans raw WhatsApp text logs and converts them into a structured DataFrame.
    Handles multi-line messages, system messages, and varying timestamp layouts.
    """
    # Regex Pattern 1: Standard 24-Hour Format -> "DD/MM/YY, HH:MM - Name: Msg"
    pattern_24h = re.compile(r'^(\d{2}/\d{2}/\d{2,4}),\s(\d{2}:\d{2})\s-\s([^:]+):\s(.*)$')
    
    # Regex Pattern 2: Standard 12-Hour Format -> "DD/MM/YY, HH:MM PM - Name: Msg"
    pattern_12h = re.compile(r'^(\d{2}/\d{2}/\d{2,4}),\s(\d{1,2}:\d{2}\s*[A-Z]{2})\s-\s([^:]+):\s(.*)$')

    cleaned_records = []
    
    with open(input_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line_str = line.strip()
            if not line_str:
                continue
                
            match = pattern_24h.match(line_str)
            time_type = "24h"
            
            if not match:
                match = pattern_12h.match(line_str)
                time_type = "12h"
                
            if match:
                date_str, time_str, sender, message = match.groups()
                
                # Exclude system notifications
                system_triggers = ["created group", "added you", "changed the group", "left the group", "was added", "messages are end-to-end encrypted"]
                if any(trigger in message.lower() for trigger in system_triggers):
                    continue
                
                cleaned_records.append({
                    'raw_date': date_str,
                    'raw_time': time_str,
                    'time_type': time_type,
                    'sender': sender.strip(),
                    'message': message.strip()
                })
            else:
                # Append multi-line content back to the last message row safely
                if cleaned_records:
                    cleaned_records[-1]['message'] += " " + line_str

    if not cleaned_records:
        raise ValueError("Could not extract structural log profiles. Check raw file layout style.")

    df = pd.DataFrame(cleaned_records)
    
    # Standardize Datetime parameters safely
    standardized_timestamps = []
    for _, row in df.iterrows():
        try:
            year_format = '%d/%m/%Y' if len(row['raw_date'].split('/')[-1]) == 4 else '%d/%m/%y'
            time_format = '%I:%M %p' if row['time_type'] == "12h" else '%H:%M'
            
            # Clean up micro-space unicode bugs placed by mobile operating systems
            clean_time_str = row['raw_time'].replace(' ', ' ').replace('  ', ' ').strip()
            
            dt = datetime.strptime(f"{row['raw_date']} {clean_time_str}", f"{year_format} {time_format}")
            standardized_timestamps.append(dt)
        except Exception:
            standardized_timestamps.append(pd.NaT)
            
    df['timestamp'] = standardized_timestamps
    df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    
    # Dimensions Feature engineering 
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    
    return df
