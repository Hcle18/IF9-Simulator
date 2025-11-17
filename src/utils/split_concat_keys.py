from src.core.librairies import *

def split_key_columns(df, list_key, split_keys):
    split_config = {item['column']: item for item in split_keys}
    updated_keys = []

    for col in list_key:
        if col in split_config:
            config = split_config[col]
            delimiter = config.get('delimiter', '__')
            regex_list = config.get('regex', None)

            max_parts = df[col].str.split(delimiter).map(len).max()
            split_cols = [f"{col}_part{i+1}" for i in range(max_parts)]
            df[split_cols] = df[col].str.split(delimiter, expand=True)
            if regex_list:
                for regex in regex_list:
                    pattern = regex.get("pattern")
                    replace = regex.get("replace")
                    for split_col in split_cols:
                        df[split_col] = df[split_col].apply(
                            lambda x: re.sub(pattern, replace, str(x)) if isinstance(x, str) else x
                            )
            updated_keys.extend(split_cols)
        else:
            updated_keys.append(col)
    return df, updated_keys

def concat_key_columns(df, list_keys, concat_keys):

    for concat in concat_keys:
        name = concat["concat_name"]
        columns = concat["columns"]
        sep = concat.get("sep", "__")
        regex_list = concat.get("regex", None)

        # Concatenate and create new column in df
        df[name] = df[columns].astype(str).agg(sep.join, axis=1)

        if regex_list:
            for regex in regex_list:
                pattern = regex.get("pattern")
                replace = regex.get("replace")
                df[name] = df[name].apply(
                    lambda x: re.sub(pattern, replace, str(x)) if isinstance(x, str) else x
                )
    final_key = []
    skip_cols = set()
    for col in list_keys:
        for concat in concat_keys:
            if col in concat["columns"] and concat["concat_name"] not in final_key:
                final_key.append(concat["concat_name"])
                skip_cols.update(concat["columns"])
        if col not in skip_cols and col not in final_key:
            final_key.append(col)
    return df, final_key