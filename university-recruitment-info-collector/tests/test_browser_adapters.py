from bs4 import BeautifulSoup

from university_recruitment.sources.university_talent_sites import (
    BrowserTalentSiteAdapter,
    HkustGzCareerAdapter,
)


def test_browser_adapter_extracts_text_only_announcements() -> None:
    adapter = BrowserTalentSiteAdapter(
        source_name="测试招聘系统",
        list_url="https://example.edu.cn/recruit",
        school="测试大学",
    )
    soup = BeautifulSoup(
        """
        <main>
          <p>人才招聘系统</p>
          <p>招聘平台操作说明</p>
          <p>测试大学2026年公开招聘辅导员公告</p>
          <p>测试大学2026年公开招聘辅导员笔试通知</p>
        </main>
        """,
        "html.parser",
    )

    jobs = adapter._extract_text_jobs_from_soup(soup)

    assert len(jobs) == 1
    # Title cleaner strips school name "测试大学" from start
    assert jobs[0].position == "2026年公开招聘辅导员公告"
    assert jobs[0].source_url == "https://example.edu.cn/recruit#text-3"


def test_hkust_gz_adapter_extracts_table_rows() -> None:
    adapter = HkustGzCareerAdapter(
        source_name="香港科技大学（广州）招聘系统",
        list_url="https://career.hkust-gz.edu.cn/",
        school="香港科技大学（广州）",
        detail_limit=2,
    )
    soup = BeautifulSoup(
        """
        <table class="el-table__body">
          <tbody>
            <tr class="jobs-table-row">
              <td><div class="cell"><span class="job-id">5900</span></div></td>
              <td><div class="cell">Technical Officer（NICE 光电工程师）</div></td>
              <td><div class="cell">Novel IC Exploration Facility (NICEF)</div></td>
            </tr>
            <tr class="jobs-table-row">
              <td><div class="cell"><span class="job-id">6018</span></div></td>
              <td><div class="cell">Vice-President for Student Affairs (VPSA)</div></td>
              <td><div class="cell">香港科技大学（广州）</div></td>
            </tr>
            <tr class="jobs-table-row">
              <td><div class="cell"><span class="job-id">6037</span></div></td>
              <td><div class="cell">Technical Officer（Mechanical）</div></td>
              <td><div class="cell">Materials Facility</div></td>
            </tr>
          </tbody>
        </table>
        """,
        "html.parser",
    )

    jobs = adapter._extract_jobs(soup)

    assert len(jobs) == 2
    assert jobs[0].school == "香港科技大学（广州）"
    assert jobs[0].position == "Technical Officer（NICE 光电工程师）"
    assert jobs[0].department == "Novel IC Exploration Facility (NICEF)"
    assert jobs[0].source_url == "https://career.hkust-gz.edu.cn#job-5900"
