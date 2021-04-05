var qObjList = [
    {
        "name":"Human glycans on P07911 with mass >= 2100.0 ",
        "query":{
            "glycan":{
                "$and":[
                    {"species.common_name": {"$eq":"Human"}},
                    {"motifs.name": {"$regex":"Polysialic","$options":"i"}},
                    {"mass": {"$gte": 2100.0}},
                    {
                        "$or":[
                            {"glycoprotein.uniprot_canonical_ac": {"$eq":"P07911"}},
                            {"glycoprotein.uniprot_canonical_ac": {"$eq": "P07911-1"}}
                        ]
                    }
                ]
            }
        }
    }
];

