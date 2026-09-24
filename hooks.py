def post_init_hook(env):
    leluhur = env['tarombo.orang'].search([('name', '=', 'Tuan Sihubil')], limit=1)
    if leluhur:
        env['ir.config_parameter'].sudo().set_param(
            'tarombo.leluhur_acuan_id', leluhur.id)
