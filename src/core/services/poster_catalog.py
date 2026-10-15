"""Visible poster choices and compatible replacements for retired library IDs."""
from pathlib import Path

LAYOUT_TEMPLATES = {
    'showcase_orange_paper': ('orange_paper', '橙白立体'),
    'showcase_editorial_cream': ('editorial_cream', '奶油杂志'),
    'showcase_checklist_lemon': ('checklist_lemon', '柠檬清单'),
    'showcase_paper_mint': ('paper_mint', '薄荷纸雕'),
    'showcase_screenshot_story': ('screenshot_story', '大截图图文'),
}

RETIRED_REPLACEMENTS = {
    'showcase_lavender_wave': 'showcase_pink_note',
    'showcase_mint_dots_wave': 'showcase_pink_note',
    'showcase_creative_poster_nature': 'showcase_minimal_lines',
    'showcase_social_story_card_tech': 'showcase_minimal_lines',
    'showcase_biz_announcement_cool': 'showcase_biz_metrics_card_alt2_professional',
    'showcase_biz_metrics_card_warm': 'showcase_biz_metrics_card_alt2_professional',
    'showcase_biz_metrics_card_alt1_nature': 'showcase_biz_metrics_card_alt2_professional',
    'showcase_edu_exam_focus_vibrant': 'showcase_edu_course_intro_elegant',
    'showcase_edu_grade_card_professional': 'showcase_edu_course_intro_elegant',
    'showcase_edu_grade_card_alt1_warm': 'showcase_edu_course_intro_elegant',
    'showcase_edu_grade_card_alt2_nature': 'showcase_edu_course_intro_elegant',
    'showcase_mkt_promo_banner_nature': 'showcase_orange_paper',
    'showcase_marketing_poster': 'showcase_orange_paper',
    'showcase_social_quote_card_vibrant': 'showcase_social_quote_card_alt2_elegant',
    'showcase_social_quote_card_alt1_professional': 'showcase_social_quote_card_alt2_elegant',
    'showcase_grid_2x2_professional': 'showcase_tech_comparison_cool',
    'showcase_cert_achievement_tech': 'showcase_minimal_lines',
}


def resolve_template_selection(template_id, layout=''):
    if template_id == 'showcase_marketing_poster':
        return next((key for key, value in LAYOUT_TEMPLATES.items() if value[0] == layout), 'showcase_orange_paper')
    return RETIRED_REPLACEMENTS.get(template_id, template_id)


def layout_for_template(template_id, fallback=''):
    return LAYOUT_TEMPLATES.get(template_id, (fallback, ''))[0]


def bundled_layout(path):
    """Only repository previews opt into a layout; uploaded names are arbitrary."""
    if not path:
        return ''
    candidate = Path(path).resolve()
    directory = Path(__file__).resolve().parents[3] / 'assets/system_templates/template_showcase'
    if candidate.parent == directory.resolve():
        return layout_for_template(candidate.stem)
    return ''
