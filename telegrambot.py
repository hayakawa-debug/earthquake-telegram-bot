        # マグニチュード
        magnitude_tag = root.find(".//body:Magnitude", ns)
        magnitude = magnitude_tag.get("description") if magnitude_tag is not None else "不明"

        # 深さ
        coord_tag = root.find(".//body:Hypocenter/body:Area/eb:Coordinate", ns)
        depth = "不明"
        if coord_tag is not None and "深さ" in coord_tag.get("description", ""):
            depth = coord_tag.get("description").split("深さ")[-1].replace("　", "").replace("km", "km")
