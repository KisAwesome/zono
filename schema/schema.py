def validate_line(line, depth):
    if len(line) > 3:
        raise ValueError(
            f"{depth} schema is incomplete should be in the format (type,validator,default)"
        )

    if line[1] is not None:
        if not callable(line[1]):
            raise ValueError(f"{depth} validator function needs to be callable")

    if not callable(line[0]):
        raise ValueError(f"{depth} type must be callable")


def validate_schema(schema, depth=""):
    if depth != "":
        depth = depth + "."
    if isinstance(schema, dict):
        for k, v in schema.items():
            if isinstance(v, dict):
                validate_schema(v, depth + k)
                continue
            validate_line(v, depth + k)
    else:
        validate_line(schema, depth)


def get_children(instance, key):
    children = []
    for k, v in instance.items():
        depth = f"{key}.{k}"
        if isinstance(v, dict):
            children.extend(get_children(v, depth))
            continue
        children.append((depth, v[2], v[0]))
    return children

def process_function_results(results):
    if isinstance(results, bool):
        return [results,'']
    return list(results)

def _validate(instance, schema, depth):
    errors = []
    if depth != "":
        depth = f"{depth}."
    if isinstance(schema, dict):
        for k, v in schema.items():
            if k not in instance:
                if isinstance(v, dict):
                    default = None
                else:
                    default = v[2]
                errors.append(
                    dict(
                        type="missingitem",
                        key=k,
                        default=default,
                        msg=f"Key {depth}{k} is missing from instance",
                    )
                )
                if isinstance(v, dict):
                    for i in get_children(v, depth + k):
                        j = i[0]
                        errors.append(
                            dict(
                                type="missingitem",
                                key=i[0],
                                default=i[1],
                                msg=f"Key {j} is missing from instance",
                            )
                        )
                continue

            if isinstance(v, dict):
                errors.extend(_validate(instance[k], v, depth + k))
                continue
            if not isinstance(instance[k], v[0]):
                errors.append(
                    dict(
                        type="incorrect_type",
                        key=depth + k,
                        default=v[2],
                        msg=f"expected type {type(v[0])} got type {type(instance[k])}",
                    )
                )
                continue
            func = v[1]
            if func is None:
                func = lambda x: (True, "")
            results = process_function_results(func(instance[k]))
            if results[0] is False or results[0] is None:
                msg = f"Unable to validate {depth}{k}"
                if len(results) > 1:
                    msg = f"An error occurred while validating {depth}{k}: {results[1]}"
                errors.append(dict(type="validationerror", key=depth + k, msg=msg,default=results[1]))
                continue

    else:
        if not isinstance(instance, schema[0]):
            errors.append(
                dict(
                    type="incorrect_type",
                    key=None,
                    default=schema[2],
                    msg=f"Expected type {type(schema[0]())} got type {type(instance)}",
                )
            )

        func = schema[1]
        if not callable(func):
            results = [True,'']
        else:
            results = process_function_results(func(instance))
        if results[0] is False or results[0] is None:
            msg = f"Unable to validate"
            if len(results) > 1:
                msg = f"An error occurred while validating: body"
            errors.append(dict(type="validationerror", key=None, msg=msg,default=results[1]))

    return errors


def validate(instance, schema):
    return _validate(instance, schema, "")


class Validator:
    def __init__(self, schema):
        validate_schema(schema)
        self.schema = schema

    def validate(self, instance):
        return validate(instance, self.schema)
