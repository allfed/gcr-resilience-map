#


### setup_logging
[source](https://github.com/allfed/gcr-resilience-map/blob/master/src/utils.py/#L8)
```python
.setup_logging(
   config: Dict[str, Any]
)
```

---
Set up logging based on configuration.

----


### save_results
[source](https://github.com/allfed/gcr-resilience-map/blob/master/src/utils.py/#L16)
```python
.save_results(
   df: pd.DataFrame, filename: str
)
```

---
Save results to a CSV file.

----


### save_to_ris
[source](https://github.com/allfed/gcr-resilience-map/blob/master/src/utils.py/#L22)
```python
.save_to_ris(
   articles: List[Dict[str, Any]], filename: str
)
```

---
Save all articles to a single RIS file.

----


### compute_symmetric_difference
[source](https://github.com/allfed/gcr-resilience-map/blob/master/src/utils.py/#L45)
```python
.compute_symmetric_difference(
   df1: pd.DataFrame, df2: pd.DataFrame
)
```

---
Compute the symmetric difference between two DataFrames.

----


### analyze_symmetric_difference
[source](https://github.com/allfed/gcr-resilience-map/blob/master/src/utils.py/#L54)
```python
.analyze_symmetric_difference(
   df1: pd.DataFrame, df2: pd.DataFrame, name1: str, name2: str, output_dir: str
)
```

---
Analyze and return a string report of the symmetric difference between two DataFrames.
