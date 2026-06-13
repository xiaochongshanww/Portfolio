"""School metadata for matching and classification.

School attributes are stored here rather than hardcoded in the matcher.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SchoolMeta:
    name: str
    is_public: bool = True       # 公办 / 民办
    is_double_first_class: bool = False  # 双一流
    is_985: bool = False
    is_211: bool = False
    is_undergraduate: bool = True  # 本科院校 / 高职院校
    aliases: tuple[str, ...] = ()  # Alternative names


# Guangzhou universities metadata
SCHOOL_METADATA: dict[str, SchoolMeta] = {
    "中山大学": SchoolMeta("中山大学", is_public=True, is_double_first_class=True, is_985=True, is_211=True),
    "华南理工大学": SchoolMeta("华南理工大学", is_public=True, is_double_first_class=True, is_985=True, is_211=True),
    "暨南大学": SchoolMeta("暨南大学", is_public=True, is_double_first_class=True, is_211=True),
    "华南师范大学": SchoolMeta("华南师范大学", is_public=True, is_double_first_class=True, is_211=True),
    "华南农业大学": SchoolMeta("华南农业大学", is_public=True, is_double_first_class=True),
    "广州医科大学": SchoolMeta("广州医科大学", is_public=True, is_double_first_class=True),
    "广州中医药大学": SchoolMeta("广州中医药大学", is_public=True, is_double_first_class=True),
    "南方医科大学": SchoolMeta("南方医科大学", is_public=True),
    "广东工业大学": SchoolMeta("广东工业大学", is_public=True),
    "广东外语外贸大学": SchoolMeta("广东外语外贸大学", is_public=True),
    "广州大学": SchoolMeta("广州大学", is_public=True),
    "广东财经大学": SchoolMeta("广东财经大学", is_public=True),
    "仲恺农业工程学院": SchoolMeta("仲恺农业工程学院", is_public=True),
    "广东药科大学": SchoolMeta("广东药科大学", is_public=True),
    "广东技术师范大学": SchoolMeta("广东技术师范大学", is_public=True),
    "广州体育学院": SchoolMeta("广州体育学院", is_public=True),
    "广州美术学院": SchoolMeta("广州美术学院", is_public=True),
    "星海音乐学院": SchoolMeta("星海音乐学院", is_public=True),
    "广东第二师范学院": SchoolMeta("广东第二师范学院", is_public=True),
    "广东警官学院": SchoolMeta("广东警官学院", is_public=True),
    "广州航海学院": SchoolMeta("广州航海学院", is_public=True),
    "香港科技大学（广州）": SchoolMeta("香港科技大学（广州）", is_public=True),

    # 民办本科
    "广东白云学院": SchoolMeta("广东白云学院", is_public=False),
    "广东培正学院": SchoolMeta("广东培正学院", is_public=False),
    "广州南方学院": SchoolMeta("广州南方学院", is_public=False),
    "广州华商学院": SchoolMeta("广州华商学院", is_public=False),
    "广州理工学院": SchoolMeta("广州理工学院", is_public=False),
    "广州软件学院": SchoolMeta("广州软件学院", is_public=False),
    "广州商学院": SchoolMeta("广州商学院", is_public=False),
    "广州华立学院": SchoolMeta("广州华立学院", is_public=False),
    "广州应用科技学院": SchoolMeta("广州应用科技学院", is_public=False),
    "广州工商学院": SchoolMeta("广州工商学院", is_public=False),
    "广州新华学院": SchoolMeta("广州新华学院", is_public=False),
    "广东外语外贸大学南国商学院": SchoolMeta("广东外语外贸大学南国商学院", is_public=False),
    "华南农业大学珠江学院": SchoolMeta("华南农业大学珠江学院", is_public=False),
    "广州城市理工学院": SchoolMeta("广州城市理工学院", is_public=False),

    # 高职院校
    "广州科技职业技术大学": SchoolMeta("广州科技职业技术大学", is_public=False, is_undergraduate=False),
    "广东轻工职业技术大学": SchoolMeta("广东轻工职业技术大学", is_public=True, is_undergraduate=False),
    "广州职业技术大学": SchoolMeta("广州职业技术大学", is_public=True, is_undergraduate=False),
    "广东交通职业技术学院": SchoolMeta("广东交通职业技术学院", is_public=True, is_undergraduate=False),
    "广东水利电力职业技术学院": SchoolMeta("广东水利电力职业技术学院", is_public=True, is_undergraduate=False),
    "广州城市职业学院": SchoolMeta("广州城市职业学院", is_public=True, is_undergraduate=False),
    "广州城建职业学院": SchoolMeta("广州城建职业学院", is_public=False, is_undergraduate=False),
    "广州南洋理工职业学院": SchoolMeta("广州南洋理工职业学院", is_public=False, is_undergraduate=False),
    "广东南华工商职业学院": SchoolMeta("广东南华工商职业学院", is_public=True, is_undergraduate=False),
    "广东建设职业技术学院": SchoolMeta("广东建设职业技术学院", is_public=True, is_undergraduate=False),
    "广东科贸职业学院": SchoolMeta("广东科贸职业学院", is_public=True, is_undergraduate=False),
    "广州工程技术职业学院": SchoolMeta("广州工程技术职业学院", is_public=True, is_undergraduate=False),
    "广东理工职业学院": SchoolMeta("广东理工职业学院", is_public=True, is_undergraduate=False),
    "广东行政职业学院": SchoolMeta("广东行政职业学院", is_public=True, is_undergraduate=False),
    "广东省外语艺术职业学院": SchoolMeta("广东省外语艺术职业学院", is_public=True, is_undergraduate=False),
    "广州卫生职业技术学院": SchoolMeta("广州卫生职业技术学院", is_public=True, is_undergraduate=False),
    "广东岭南职业技术学院": SchoolMeta("广东岭南职业技术学院", is_public=False, is_undergraduate=False),
    "广州铁路职业技术学院": SchoolMeta("广州铁路职业技术学院", is_public=True, is_undergraduate=False),
    "广东生态工程职业学院": SchoolMeta("广东生态工程职业学院", is_public=True, is_undergraduate=False),
    "私立华联学院": SchoolMeta("私立华联学院", is_public=False, is_undergraduate=False),
    "广州华南商贸职业学院": SchoolMeta("广州华南商贸职业学院", is_public=False, is_undergraduate=False),
    "广州华夏职业学院": SchoolMeta("广州华夏职业学院", is_public=False, is_undergraduate=False),
    "广州东华职业学院": SchoolMeta("广州东华职业学院", is_public=False, is_undergraduate=False),
    "广州华商职业学院": SchoolMeta("广州华商职业学院", is_public=False, is_undergraduate=False),
    "广州华立科技职业学院": SchoolMeta("广州华立科技职业学院", is_public=False, is_undergraduate=False),
    "广东体育职业技术学院": SchoolMeta("广东体育职业技术学院", is_public=True, is_undergraduate=False),
    "广东艺术职业学院": SchoolMeta("广东艺术职业学院", is_public=True, is_undergraduate=False),
    "广州科技贸易职业学院": SchoolMeta("广州科技贸易职业学院", is_public=True, is_undergraduate=False),
    "广州民航职业技术学院": SchoolMeta("广州民航职业技术学院", is_public=True, is_undergraduate=False),
    "广东机电职业技术学院": SchoolMeta("广东机电职业技术学院", is_public=True, is_undergraduate=False),
    "广东邮电职业技术学院": SchoolMeta("广东邮电职业技术学院", is_public=True, is_undergraduate=False),
    "广东科学技术职业学院": SchoolMeta("广东科学技术职业学院", is_public=True, is_undergraduate=False),
    "广州松田职业学院": SchoolMeta("广州松田职业学院", is_public=False, is_undergraduate=False),
    "广东食品药品职业学院": SchoolMeta("广东食品药品职业学院", is_public=True, is_undergraduate=False),
    "广东工贸职业技术学院": SchoolMeta("广东工贸职业技术学院", is_public=True, is_undergraduate=False),
    "广州康大职业技术学院": SchoolMeta("广州康大职业技术学院", is_public=False, is_undergraduate=False),
}


def get_school_meta(school_name: str) -> SchoolMeta | None:
    """Look up school metadata, supporting aliases."""
    if school_name in SCHOOL_METADATA:
        return SCHOOL_METADATA[school_name]
    for meta in SCHOOL_METADATA.values():
        if school_name in meta.aliases:
            return meta
    return None


def school_matches_type(school_name: str, type_filter: str) -> bool:
    """Check if a school matches a type filter from user preferences.

    Supported filters: 双一流, 985, 211, 公办, 民办, 本科院校, 高职院校
    """
    meta = get_school_meta(school_name)
    if not meta:
        return False
    mapping = {
        "双一流": meta.is_double_first_class,
        "985": meta.is_985,
        "211": meta.is_211,
        "公办": meta.is_public,
        "民办": not meta.is_public,
        "本科院校": meta.is_undergraduate,
        "高职院校": not meta.is_undergraduate,
    }
    return mapping.get(type_filter, False)
