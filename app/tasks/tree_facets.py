"""
Queue tasks related to tree facets.
"""

from app.dependencies import TenantDbDep, ElasticIndexDep, DatasetDep
from app.services.search.dataclasses import FilterOptions


async def construct_tree(facet_name: str, dataset: DatasetDep, db: TenantDbDep,
                         es_index: ElasticIndexDep):
    """
    Construct a tree for a facet.
    :param facet_name:
    :param es_index:
    :param db:
    :param dataset:
    :return:
    """
    print(facet_name)

    cursor = db['facets'].find({
        "dataset_name": dataset.name,
        "property": facet_name
    })
    facet_data = (await cursor.to_list())[0]

    filter_options = FilterOptions([])

    tree = es_index.get_tree(facet_name, filter_options)

    def add_node(node, parent):
        db["nodes"].insert_one({
            "_id": f"{facet_data["_id"]}_{node["value"]}",
            "facet_name": facet_name,
            "dataset": dataset.name,
            "parent": parent["value"] if parent is not None else None,
            "value": node["value"],
            "name": node["name"],
            "has_children": len(node["children"]) > 0,
        })

    def iterate_tree(node, parent = None):
        for child in node["children"]:
            iterate_tree(child, node)
        add_node(node, parent)

    for n in tree:
        iterate_tree(n)
