# (type,validate,default)
import zono.schema
import json


def add_value(d, path, value):
    curr = d
    for key in path:
        if key not in curr:
            curr[key] = {}
        if curr[key] is None:
            curr[key] = {}
        curr = curr[key]
    k, v = value
    curr[k] = v

    return d


class FailedToDecode(Exception):
    pass




def load_json_file(file_path):
    try:
        with open(file_path) as json_file:
            return json.load(json_file)
    except json.JSONDecodeError as e:
        with open(file_path, "r") as json_file:
            json_data = json_file.read()
            fixed_json_data = (
                json_data.replace("\n", "").replace("\r", "").replace("\t", "")
            )
            if not fixed_json_data.startswith("[") and not fixed_json_data.startswith(
                "{"
            ):
                fixed_json_data = "[" + fixed_json_data + "]"
            try:
                json_obj = json.loads(fixed_json_data)
                with open(file_path, "w") as json_file:
                    json.dump(json_obj, json_file, indent=4)
                return json_obj
            except json.JSONDecodeError as e:
                if str(e).startswith(
                    "Expecting property name enclosed in double quotes"
                ):
                    idx = str(e).rfind(":")
                    pos = int(str(e)[idx + 1 :])
                    json_data = json_data[:pos] + '"' + json_data[pos:]
                    fixed_json_data = (
                        json_data.replace("\n", "").replace("\r", "").replace("\t", "")
                    )
                    try:
                        json_obj = json.loads(fixed_json_data)
                        with open(file_path, "w") as json_file:
                            json.dump(json_obj, json_file, indent=4)
                        return json_obj
                    except json.JSONDecodeError as e:
                        return FailedToDecode()
                else:
                    return FailedToDecode()
    except Exception as e:
        return FailedToDecode()


class Settings:
    def __init__(self, path, schema, fix=True):
        self.path = path
        self.schema = schema
        self.validator = zono.schema.Validator(schema)
        self.fix = fix
        self.load()

    def get_defaults(self, ins=None):
        ins = ins or self.schema
        if isinstance(ins, dict):
            defaults = {}
            for k, v in ins.items():
                if isinstance(v, dict):
                    defaults[k] = self.get_defaults(v)
                    continue
                defaults[k] = v[2]

            return defaults

        else:
            return ins[2]

    def _fix_path(self, path):
        if isinstance(path, str):
            return path.split(".")
        else:
            return path

    def set_value(self, path, values):
        path = self._fix_path(path)
        self.settings = add_value(self.settings, path, values)
        self.save()

    def get_value(self, path):
        path = self._fix_path(path)
        curr = self.settings
        for i in path:
            curr = curr[i]
        return curr

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.settings, f)

    def load(self):
        settings = load_json_file(self.path)
        if isinstance(settings, FailedToDecode):
            self.errors = []
            self.settings = self.get_defaults()
            return self.save()

        self.errors = self.validator.validate(settings)

        if isinstance(self.schema, dict) and not isinstance(settings, dict):
            self.settings = self.get_defaults()
            return self.save()

        for i in self.errors:
            if isinstance(self.schema, dict):
                x = i["key"].split(".")
                end = x.pop()
                add_value(settings, x, (end, i["default"]))
            else:
                settings = i["default"]

        self.settings = settings
        if self.fix and len(self.errors) > 0:
            self.save()


def v(x):
    state = True
    if x not in range(100):
        state = False
    return state,50

if __name__ == "__main__":
    s = Settings("test.json", (int, v, -1))


    print(s.errors)
    # print(s.settings)