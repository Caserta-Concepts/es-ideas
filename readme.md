# Elasticsearch Analysis

## Inputs

This article and accompanying github has the starter for a Dataflow based pipeline to ES:
https://medium.com/google-cloud/using-cloud-dataflow-to-index-documents-into-elasticsearch-b3a31e999dfc
And this one has some BigQuery bits: https://medium.com/weareservian/how-to-transfer-bigquery-tables-between-locations-with-cloud-dataflow-9582acc6ae1d

Between the two it seems reasonable to assume getting the data into ES from BQ is, while not trivial, not daunting either.

The bigger hassle is the cost of managing the ES setup.

https://www.elastic.co/about/partners/google-cloud-platform
https://www.elastic.co/blog/elastic-and-google-team-up-to-bring-a-more-native-elasticsearch-service-experience-on-google-cloud

In any event, for a basic POC we can do the following:

Steps for "more like this" sample

* Pulled the "Clinical" data from TGA
* Put it in ES 7.0.1 (local, automapping)
```
curl -X PUT "localhost:9200/tga_clinical" -H 'Content-Type: application/json' -d'
{
    "settings" : {
        "index" : {
            "number_of_shards" : 3, 
            "number_of_replicas" : 2 
        }
    }
}
'
```

If needed, convert the clinical data to "es bulk compatible" file with the script 

`python convert_clinical_to_es_bulk.py`

Then push it into ES:

`curl -X POST "localhost:9200/tga_clinical/_bulk"  -H 'Content-Type: application/x-ndjson' --data-binary "@clinical_bulk.json"`

Finally check the index has the data:

`curl localhost:9200/tga_clinical/_stats?pretty`

Should see something like:

```
"indices" : {
    "tga_clinical" : {
      "uuid" : "g7jsD-AcSpKKc6rJyoT_Fg",
      "primaries" : {
        "docs" : {
          "count" : 11156,
          "deleted" : 0
        },
```
where we can see 11K docs in the index now.  So...data is present. (yay!)        


## API Queries

https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-mlt-query.html

Now lets run an API-only "more like this" query using some data point. Reviewing our feed clinical.json we see country: Poland.  OK.

```
curl -X GET "localhost:9200/tga_clinical/_search?pretty" -H 'Content-Type: application/json' -d'
{
    "query": {
        "more_like_this" : {
            "fields" : ["country"],
            "like" : "Poland",
            "min_term_freq" : 1,
            "max_query_terms" : 12
        }
    }
}
'
```

```
  "hits" : {
    "total" : {
      "value" : 204,
      "relation" : "eq"
    },
```


Ok that wasn't very interesting. How about querying ALL non-numeric fields, for others from Poland who have rectal issues?

```curl -X GET "localhost:9200/tga_clinical/_search?pretty" -H 'Content-Type: application/json' -d'
{
    "query": {
        "more_like_this" : {
            "fields" : [
	"ParticipantBarcode",
	"Study",
	"Project",
	"TSSCode",
	"age_at_initial_pathologic_diagnosis",
	"anatomic_neoplasm_subdivision",
	"batch_number",
	"bcr",
	"country",
	"vital_status",
	"days_to_birth",
	"days_to_death",
	"days_to_last_known_alive",
	"days_to_initial_pathologic_diagnosis",
	"ethnicity",
	"gender",
	"histological_type",
	"history_of_neoadjuvant_treatment",
	"icd_10",
	"icd_o_3_histology",
	"icd_o_3_site",
	"lymphovascular_invasion_present",
	"neoplasm_histologic_grade",
	"new_tumor_event_after_initial_treatment",
	"year_of_initial_pathologic_diagnosis",
	"pathologic_M",
	"pathologic_N",
	"pathologic_T",
	"pathologic_stage",
	"person_neoplasm_cancer_status",
	"primary_therapy_outcome_success",
	"race",
	"tobacco_smoking_history",
	"tumor_tissue_site",
	"age_began_smoking_in_years",
	"other_dx",
	"other_malignancy_anatomic_site",
	"other_malignancy_histological_type",
	"other_malignancy_malignancy_type",
	"stopped_smoking_year"
	],
            "like" : "Poland Rectal",
            "min_term_freq" : 1,
            "max_query_terms" : 12
        }
    }
}
'```

```
   "total" : {
      "value" : 350,
      "relation" : "eq"
    },
```

 
Hm...what if we also make it "only men". Should get a smaller set right?

curl -X GET "localhost:9200/tga_clinical/_search?pretty" -H 'Content-Type: application/json' -d'
{
    "query": {
        "more_like_this" : {
            "fields" : [
	"ParticipantBarcode",
	"Study",
	"Project",
	"TSSCode",
	"age_at_initial_pathologic_diagnosis",
	"anatomic_neoplasm_subdivision",
	"batch_number",
	"bcr",
	"country",
	"vital_status",
	"days_to_birth",
	"days_to_death",
	"days_to_last_known_alive",
	"days_to_initial_pathologic_diagnosis",
	"ethnicity",
	"gender",
	"histological_type",
	"history_of_neoadjuvant_treatment",
	"icd_10",
	"icd_o_3_histology",
	"icd_o_3_site",
	"lymphovascular_invasion_present",
	"neoplasm_histologic_grade",
	"new_tumor_event_after_initial_treatment",
	"year_of_initial_pathologic_diagnosis",
	"pathologic_M",
	"pathologic_N",
	"pathologic_T",
	"pathologic_stage",
	"person_neoplasm_cancer_status",
	"primary_therapy_outcome_success",
	"race",
	"tobacco_smoking_history",
	"tumor_tissue_site",
	"age_began_smoking_in_years",
	"other_dx",
	"other_malignancy_anatomic_site",
	"other_malignancy_histological_type",
	"other_malignancy_malignancy_type",
	"stopped_smoking_year"
	],
            "like" : "Poland Rectal Male",
            "min_term_freq" : 1,
            "max_query_terms" : 12
        }
    }
}
'

```
  "hits" : {
    "total" : {
      "value" : 5529,
      "relation" : "eq"
    },
```

So now we're getting even more hits...dang. So the "more like this" will widen the search based on the search terms - more terms == more hits.

What we see here is that the "more like this" canned filter may work OK but doesn't support numeric things that probably really matter like "number of lymph nodes affected" and "number pack years smoked" - so probably it would be combined with other filters to be optimal.

However - the top searches with the highest scores are likely the most accurate...so...maybe that works.

If not, then what we really want to do is more "faceted" type of search and not so full-texty, with clues about ranking.

curl -X GET "localhost:9200/tga_clinical/_search?pretty" -H 'Content-Type: application/json' -d'{
  "query": {
    "bool" : {
      "must" : {
        "match" : { "tumor_tissue_site" : "Rectum" }
      },
      "filter": {
        "match" : { "gender" : "MALE" }
      },
      "must_not" : {
        "range" : {
          "age_at_initial_pathologic_diagnosis" : { "gte" : 50, "lte" : 70 }
        }
      },
      "should" : [
        { "match" : { "country" : "Poland" } }
      ],
      "minimum_should_match" : 1,
      "boost" : 1.0
    }
  }
}'

This is pretty much the same query, but using much more explicit search. Note we're down to 2 results, and one of them doesn't even fit (the age is 33 on the second hit).
```
  "hits" : {
    "total" : {
      "value" : 2,
      "relation" : "eq"
    },
```



TONNES more would need to be done here to make this really useful. Tuning analyzers and ontologies...

https://opensourceconnections.com/blog/2016/12/23/elasticsearch-synonyms-patterns-taxonomies/

Or even being able to search by Genomic Similarity
https://blog.color.com/a-search-engine-for-the-human-genome-part-i-the-genome-in-software-d66b82323888




## Outputs

Most UI's for Elasticsearch (SenseUI, Dejavu are made for making it easier to query, using Elasticsearch query & filter DSL.
This is simply not suitable for "business users". 

Others (Kibana, Grafana) are made for doing charting and analysis using funky custom wrappers for ES DSL, but not necessarily querying. These are typically designed around analyzing logs.

`max_over_time(deriv(rate(distance_covered_total[5s])[30s:5s])[10m:])`
`topk(3, sum(rate(instance_cpu_time_ns[5m])) by (app, proc))`

Note: (@Joe) Kibana NOT made for interactive query/drilldown

https://discuss.elastic.co/t/drill-down-on-charts/94178


Most interesting are:


### DejaVu: https://github.com/appbaseio/dejavu#visual-filters a "single page webapp"

Run a docker
```
docker run -p 1358:1358 -d appbaseio/dejavu
open http://localhost:1358/
```

I also had to hack in CORS stuf to the config yaml which is indicated in the app front screen.


Demo of me monkeying with DejaVu: https://drive.google.com/file/d/1BPy5PRAg4xOVd1wHeaPSIj6rw-YRTaBp/view?usp=sharing


### Elastic-Kaizen: https://www.elastic-kaizen.com/ a "downloadable desktop client built in Java"

Download, unzip, and run a Jar, e.g. `java -jar Kaizen.jar`

Demo of me monkeying with Elastic-Kaizen: https://drive.google.com/file/d/1RxH83m6KkEtmRTa2BWcwn3CpnOnCAN_u/view?usp=sharing


From the videos, one might ask "how is this any different from filtering an excel sheet?" - and you wouldn't be wrong. But you would be overlooking a lot of the magic ES is capable of doing for us in the Analyzers and Taxonomies that could be set up, not to mention the amount of data that can be stored, clustering, multi-user, performance...etc.

gender: MALE AND country: United AND icd_10: C01 AND vital_status: "Alive"

But still these have nothing on a custom-built querying experience with known index terms.




