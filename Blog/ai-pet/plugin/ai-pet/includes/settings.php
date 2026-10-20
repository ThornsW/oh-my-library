<?php
/**
 * 后台「AI 宠物 → 设置」。一级菜单「AI 宠物」本身是聊天记录页（log.php）。
 *
 * 普通设置存在 aipet_settings（自动加载）；API key 单独存在 aipet_api_key，
 * 不自动加载、保存后不再回显，只在调用接口时读取。
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

const AIPET_OPTION     = 'aipet_settings';
const AIPET_KEY_OPTION = 'aipet_api_key';

/** 访客 IP 从哪里取：键是设置值，值是 $_SERVER 里的字段（空字符串表示直接用 REMOTE_ADDR）。 */
const AIPET_IP_SOURCES = array(
	'remote'     => '',
	'cloudflare' => 'HTTP_CF_CONNECTING_IP',
	'xreal'      => 'HTTP_X_REAL_IP',
	'xff'        => 'HTTP_X_FORWARDED_FOR',
);

/** 默认人设：用站名和角色名拼出来。$name 为空时读已保存的角色名。 */
function aipet_default_persona( $name = '' ) {
	if ( '' === $name ) {
		$saved = (array) get_option( AIPET_OPTION, array() );
		$name  = (string) ( $saved['pet_name'] ?? '' ) ?: '小助手';
	}
	return sprintf( '你是「%s」的看板娘，名叫%s，平时待在页面左下角陪访客逛博客。性格活泼、有点黏人，说话可爱简短。', get_bloginfo( 'name' ), $name );
}

function aipet_defaults() {
	$d = array(
		'enabled'      => 1,
		'chat_enabled' => 1,
		'base_url'     => '',
		'model'        => '',
		'persona'      => aipet_default_persona(),
		'per_hour'     => 20,
		'per_day'      => 60,
		'site_day'     => 500,
		// 角色（图片位置 img_<位置> 见 character.php）
		'pet_name'     => '小助手',
		'pet_width'    => 192,
		'img_pixel'    => 0,
		// 外观
		'color_light'  => '#1F6F54',
		'color_dark'   => '#9C78E2',
		'dark_mode'    => 'auto',
		'hide_below'   => 1600,
		// 聊天记录与隐私
		'log_enabled'  => 1,
		'log_days'     => 30,
		'log_ip'       => 1,
		'notice'       => 0,
		'ip_source'    => 'remote',
	);
	foreach ( array_keys( AIPET_IMAGE_SLOTS ) as $slot ) {
		$d[ 'img_' . $slot ] = '';
	}
	return $d;
}

function aipet_opt( $key ) {
	$opts = wp_parse_args( (array) get_option( AIPET_OPTION, array() ), aipet_defaults() );
	return $opts[ $key ] ?? null;
}

function aipet_chat_ready() {
	return aipet_opt( 'enabled' ) && aipet_opt( 'chat_enabled' ) && '' !== aipet_opt( 'base_url' ) && '' !== aipet_opt( 'model' ) && '' !== (string) get_option( AIPET_KEY_OPTION, '' );
}

add_action( 'admin_init', 'aipet_register_settings' );
add_action( 'admin_menu', 'aipet_add_menu' );

function aipet_register_settings() {
	register_setting(
		'aipet',
		AIPET_OPTION,
		array(
			'type'              => 'array',
			'sanitize_callback' => 'aipet_sanitize',
			'default'           => aipet_defaults(),
		)
	);
}

function aipet_add_menu() {
	add_menu_page( 'AI 宠物', 'AI 宠物', 'manage_options', 'ai-pet', 'aipet_log_page', 'dashicons-pets', 28 );
	add_submenu_page( 'ai-pet', '聊天记录', '聊天记录', 'manage_options', 'ai-pet', 'aipet_log_page' );
	$hook = add_submenu_page( 'ai-pet', 'AI 宠物设置', '设置', 'manage_options', 'ai-pet-settings', 'aipet_settings_page' );
	// 设置页要用媒体库选角色图片
	add_action( 'load-' . $hook, fn() => add_action( 'admin_enqueue_scripts', fn() => wp_enqueue_media() ) );
}

function aipet_sanitize( $in ) {
	$in  = (array) $in;
	$d   = aipet_defaults();
	$out = array(
		'base_url'  => untrailingslashit( esc_url_raw( trim( (string) ( $in['base_url'] ?? '' ) ), array( 'https', 'http' ) ) ),
		'model'     => sanitize_text_field( (string) ( $in['model'] ?? '' ) ),
		'persona'   => sanitize_textarea_field( (string) ( $in['persona'] ?? '' ) ),
		'pet_name'  => mb_substr( sanitize_text_field( (string) ( $in['pet_name'] ?? '' ) ), 0, 20 ) ?: $d['pet_name'],
		'dark_mode' => in_array( $in['dark_mode'] ?? '', array( 'auto', 'system', 'off' ), true ) ? $in['dark_mode'] : $d['dark_mode'],
		'ip_source' => isset( AIPET_IP_SOURCES[ $in['ip_source'] ?? '' ] ) ? $in['ip_source'] : $d['ip_source'],
	);
	foreach ( array_keys( AIPET_IMAGE_SLOTS ) as $slot ) {
		$out[ 'img_' . $slot ] = esc_url_raw( trim( (string) ( $in[ 'img_' . $slot ] ?? '' ) ), array( 'https', 'http' ) );
	}
	foreach ( array( 'enabled', 'chat_enabled', 'img_pixel', 'log_enabled', 'log_ip', 'notice' ) as $k ) {
		$out[ $k ] = empty( $in[ $k ] ) ? 0 : 1;
	}
	foreach ( array( 'color_light', 'color_dark' ) as $k ) {
		$out[ $k ] = sanitize_hex_color( (string) ( $in[ $k ] ?? '' ) ) ?: $d[ $k ];
	}
	foreach ( array( 'per_hour', 'per_day', 'site_day' ) as $k ) {
		$out[ $k ] = max( 0, min( 100000, (int) ( $in[ $k ] ?? $d[ $k ] ) ) );
	}
	$out['hide_below'] = max( 0, min( 10000, (int) ( $in['hide_below'] ?? $d['hide_below'] ) ) );
	$out['pet_width']  = max( 48, min( 480, (int) ( $in['pet_width'] ?? $d['pet_width'] ) ) );
	$out['log_days']   = max( 1, min( 3650, (int) ( $in['log_days'] ?? $d['log_days'] ) ) );
	if ( '' === $out['persona'] ) {
		$out['persona'] = aipet_default_persona( $out['pet_name'] );
	}

	// API key 不在 aipet_settings 里：新填了才覆盖，勾了「清除」才删除。
	// 这个回调由 options.php 在核对 nonce 和权限之后调用。
	if ( current_user_can( 'manage_options' ) ) {
		$new = isset( $_POST['aipet_api_key_new'] ) ? trim( sanitize_text_field( wp_unslash( $_POST['aipet_api_key_new'] ) ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification
		if ( ! empty( $_POST['aipet_api_key_clear'] ) ) { // phpcs:ignore WordPress.Security.NonceVerification
			delete_option( AIPET_KEY_OPTION );
		} elseif ( '' !== $new ) {
			update_option( AIPET_KEY_OPTION, $new, false );
		}
	}
	return $out;
}

function aipet_settings_page() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	$o       = wp_parse_args( (array) get_option( AIPET_OPTION, array() ), aipet_defaults() );
	$has_key = '' !== (string) get_option( AIPET_KEY_OPTION, '' );
	$name    = AIPET_OPTION;
	$today   = (int) get_transient( 'aipet_s_' . wp_date( 'Ymd' ) );
	$field   = fn( $k ) => esc_attr( $name . '[' . $k . ']' );
	?>
	<div class="wrap">
		<h1>AI 宠物设置</h1>
		<?php settings_errors(); ?>
		<p>今天全站已聊 <strong><?php echo esc_html( $today ); ?></strong> 句（上限 <?php echo esc_html( $o['site_day'] ); ?>）。
		聊天状态：<strong><?php echo aipet_chat_ready() ? '可用' : '未就绪（需要开启聊天，并填好接口地址、API key 和模型）'; ?></strong></p>
		<p class="description">改完设置后，如果装了页面缓存插件（WP Fastest Cache、WP Super Cache 等），请清一次缓存，前台才会用上新设置。</p>
		<form method="post" action="options.php">
			<?php settings_fields( 'aipet' ); ?>
			<h2 class="title">角色</h2>
			<?php $file = aipet_character_file(); ?>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row">当前角色</th>
					<td>
						<?php if ( $file ) : ?>
							<strong>JS 角色文件</strong>：<code><?php echo esc_html( str_replace( ABSPATH, '', $file['path'] ) ); ?></code>（<?php echo esc_html( wp_date( 'Y-m-d H:i', (int) $file['ver'] ) ); ?> 修改）。有这个文件时优先用它，下面的图片不生效。
						<?php elseif ( aipet_character_images() ) : ?>
							<strong>图片角色</strong>（下面选的图片）。
						<?php else : ?>
							<strong style="color:#b32d2e">还没有角色，前台不显示。</strong>在下面至少选一张「普通」图片，或者把 JS 角色文件放到 <code><?php echo esc_html( str_replace( ABSPATH, '', trailingslashit( wp_upload_dir( null, false )['basedir'] ) ) ); ?>ai-pet/character.js</code>。
						<?php endif; ?>
						<p class="description">怎么准备角色（自己画、用 AI 生成图片或 JS 角色文件）见插件 README。</p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-name">名字</label></th>
					<td><input id="aipet-name" class="regular-text" type="text" maxlength="20" name="<?php echo $field( 'pet_name' ); ?>" value="<?php echo esc_attr( $o['pet_name'] ); ?>">
						<p class="description">用在预设台词、输入框提示和后台聊天记录里。改名后记得同步改下面的「人设」。</p></td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-width">显示宽度</label></th>
					<td><input id="aipet-width" class="small-text" type="number" min="48" max="480" name="<?php echo $field( 'pet_width' ); ?>" value="<?php echo esc_attr( $o['pet_width'] ); ?>"> px，高度按比例；手机上自动减半。</td>
				</tr>
				<tr>
					<th scope="row">角色图片</th>
					<td>
						<table class="aipet-imgs">
							<?php foreach ( AIPET_IMAGE_SLOTS as $slot => $label ) : $k = 'img_' . $slot; ?>
								<tr>
									<td><?php echo esc_html( $label ); ?></td>
									<td class="aipet-thumb"><?php if ( $o[ $k ] ) : ?><img src="<?php echo esc_url( $o[ $k ] ); ?>" alt=""><?php endif; ?></td>
									<td>
										<input id="aipet-<?php echo esc_attr( $k ); ?>" class="regular-text code" type="url" name="<?php echo $field( $k ); ?>" value="<?php echo esc_attr( $o[ $k ] ); ?>">
										<button type="button" class="button aipet-pick" data-target="aipet-<?php echo esc_attr( $k ); ?>">选择图片</button>
									</td>
								</tr>
							<?php endforeach; ?>
						</table>
						<label><input type="checkbox" name="<?php echo $field( 'img_pixel' ); ?>" value="1" <?php checked( $o['img_pixel'] ); ?>> 像素画（放大时保持锐利，不模糊）</label>
						<p class="description">只填「普通」也能用；其他表情没填时用「普通」。所有图片请用<strong>同样的画布大小</strong>和透明背景（PNG / WebP / GIF），角色下半身贴着图片底边，看起来像从屏幕底下探出头。「说话」是张嘴的那一张，说话时会和表情图来回切换。</p>
					</td>
				</tr>
			</table>

			<h2 class="title">聊天</h2>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row">开关</th>
					<td>
						<label><input type="checkbox" name="<?php echo $field( 'enabled' ); ?>" value="1" <?php checked( $o['enabled'] ); ?>> 在前台显示角色</label><br>
						<label><input type="checkbox" name="<?php echo $field( 'chat_enabled' ); ?>" value="1" <?php checked( $o['chat_enabled'] ); ?>> 允许聊天（关掉后只说预设台词）</label>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-base">接口地址</label></th>
					<td><input id="aipet-base" class="regular-text code" type="url" name="<?php echo $field( 'base_url' ); ?>" value="<?php echo esc_attr( $o['base_url'] ); ?>" placeholder="https://api.openai.com/v1">
						<p class="description">任何 OpenAI 兼容接口（OpenAI、DeepSeek、自建的 CLIProxyAPI / One API 等），写到 <code>/v1</code> 为止。</p></td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-key">API key</label></th>
					<td>
						<input id="aipet-key" class="regular-text" type="password" name="aipet_api_key_new" value="" autocomplete="new-password" placeholder="<?php echo $has_key ? '已设置，留空表示不修改' : '未设置'; ?>">
						<?php if ( $has_key ) : ?>
							<label style="margin-left:8px"><input type="checkbox" name="aipet_api_key_clear" value="1"> 清除</label>
						<?php endif; ?>
						<p class="description">保存后不再显示。建议给博客单独建一个 key，出问题时可以单独作废。</p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-model">模型</label></th>
					<td>
						<input id="aipet-model" class="regular-text code" type="text" list="aipet-models" name="<?php echo $field( 'model' ); ?>" value="<?php echo esc_attr( $o['model'] ); ?>">
						<datalist id="aipet-models"></datalist>
						<button type="button" class="button" id="aipet-fetch-models">获取模型列表</button>
						<span id="aipet-models-msg" class="description"></span>
						<p class="description">用已保存的接口地址和 key 读取 <code>/models</code>。改了地址或 key 先保存再获取。回答慢的话换一个不带深度思考的轻量模型。</p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-persona">人设</label></th>
					<td><textarea id="aipet-persona" class="large-text" rows="4" name="<?php echo $field( 'persona' ); ?>"><?php echo esc_textarea( $o['persona'] ); ?></textarea>
						<p class="description">聊天规则（只聊博客相关话题、回答简短、只推荐站内内容）由插件自动追加，不用写在这里。清空后恢复默认。</p></td>
				</tr>
				<tr>
					<th scope="row">限额</th>
					<td>
						每个访客每小时 <input type="number" min="0" class="small-text" name="<?php echo $field( 'per_hour' ); ?>" value="<?php echo esc_attr( $o['per_hour'] ); ?>"> 句，
						每天 <input type="number" min="0" class="small-text" name="<?php echo $field( 'per_day' ); ?>" value="<?php echo esc_attr( $o['per_day'] ); ?>"> 句；
						全站每天 <input type="number" min="0" class="small-text" name="<?php echo $field( 'site_day' ); ?>" value="<?php echo esc_attr( $o['site_day'] ); ?>"> 句。
						<p class="description">超出后角色改说预设台词。</p>
					</td>
				</tr>
			</table>

			<h2 class="title">外观</h2>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row">主色</th>
					<td>
						<label>日间 <input type="color" name="<?php echo $field( 'color_light' ); ?>" value="<?php echo esc_attr( $o['color_light'] ); ?>"></label>
						<label style="margin-left:16px">夜间 <input type="color" name="<?php echo $field( 'color_dark' ); ?>" value="<?php echo esc_attr( $o['color_dark'] ); ?>"></label>
						<p class="description">对话气泡的边框、链接和发送按钮用这个颜色，建议和博客主题色一致。</p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-dark">夜间模式</label></th>
					<td>
						<select id="aipet-dark" name="<?php echo $field( 'dark_mode' ); ?>">
							<option value="auto" <?php selected( $o['dark_mode'], 'auto' ); ?>>跟随主题的夜间模式（自动识别）</option>
							<option value="system" <?php selected( $o['dark_mode'], 'system' ); ?>>跟随访客的系统设置</option>
							<option value="off" <?php selected( $o['dark_mode'], 'off' ); ?>>不用夜间配色</option>
						</select>
						<p class="description">自动识别：<code>&lt;html&gt;</code> 或 <code>&lt;body&gt;</code> 带 <code>darkmode</code>（Argon）、<code>dark</code>、<code>dark-mode</code> 等类名，或 <code>data-theme="dark"</code> 这类属性时，算作夜间。主题本身没有夜间模式时选「不用」。</p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-hide">窄屏默认躲起来</label></th>
					<td>
						浏览器窗口窄于 <input id="aipet-hide" type="number" min="0" step="10" class="small-text" name="<?php echo $field( 'hide_below' ); ?>" value="<?php echo esc_attr( $o['hide_below'] ); ?>"> px 时，打开页面只露出耳朵，点一下才出来。
						<p class="description">角色会压住左侧栏的主题可以设大一点（Argon 约 1600）；没有左侧栏的主题填 0 表示一直出来。访客自己点过躲起来或叫出来之后，按访客的选择来。</p>
					</td>
				</tr>
			</table>

			<h2 class="title">聊天记录与隐私</h2>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row">聊天记录</th>
					<td>
						<label><input type="checkbox" name="<?php echo $field( 'log_enabled' ); ?>" value="1" <?php checked( $o['log_enabled'] ); ?>> 保存聊天记录</label>，保留
						<input type="number" min="1" class="small-text" name="<?php echo $field( 'log_days' ); ?>" value="<?php echo esc_attr( $o['log_days'] ); ?>"> 天，过期每天自动删除。<br>
						<label><input type="checkbox" name="<?php echo $field( 'log_ip' ); ?>" value="1" <?php checked( $o['log_ip'] ); ?>> 记录访客 IP 原文</label>（不勾时只记一个匿名编号，同一个访客的对话仍能归到一起）<br>
						<label><input type="checkbox" name="<?php echo $field( 'notice' ); ?>" value="1" <?php checked( $o['notice'] ); ?>> 在聊天框下面提示访客「聊天内容会被站长看到」</label>
						<p class="description">IP 和聊天内容属于个人信息。请按你所在地区的法规（如中国《个人信息保护法》、欧盟 GDPR）决定是否记录、是否提示访客，必要时写进网站的隐私政策。</p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="aipet-ip">访客 IP 来源</label></th>
					<td>
						<select id="aipet-ip" name="<?php echo $field( 'ip_source' ); ?>">
							<option value="remote" <?php selected( $o['ip_source'], 'remote' ); ?>>直接连接（REMOTE_ADDR）</option>
							<option value="cloudflare" <?php selected( $o['ip_source'], 'cloudflare' ); ?>>Cloudflare（CF-Connecting-IP）</option>
							<option value="xreal" <?php selected( $o['ip_source'], 'xreal' ); ?>>反向代理（X-Real-IP）</option>
							<option value="xff" <?php selected( $o['ip_source'], 'xff' ); ?>>反向代理（X-Forwarded-For 最后一个）</option>
						</select>
						<p class="description">用于限流和聊天记录。网站前面有 CDN 或反向代理时，不改的话所有访客会被当成同一个 IP。<strong>没有经过对应代理时不要选后三项</strong>，否则访客可以伪造 IP 绕过限流。</p>
					</td>
				</tr>
			</table>
			<?php submit_button(); ?>
		</form>
	</div>
	<style>
		.aipet-imgs td { padding: 4px 8px 4px 0; vertical-align: middle; }
		.aipet-thumb { width: 48px; }
		.aipet-thumb img { max-width: 48px; max-height: 48px; display: block; }
	</style>
	<script>
	(function () {
		document.querySelectorAll('.aipet-pick').forEach(btn => btn.addEventListener('click', () => {
			const input = document.getElementById(btn.dataset.target);
			const frame = wp.media({ title: '选择角色图片', library: { type: 'image' }, multiple: false, button: { text: '使用这张图片' } });
			frame.on('select', () => {
				input.value = frame.state().get('selection').first().toJSON().url;
				const cell = input.closest('tr').querySelector('.aipet-thumb');
				cell.replaceChildren(Object.assign(document.createElement('img'), { src: input.value, alt: '' }));
			});
			frame.open();
		}));
	})();
	(function () {
		const btn = document.getElementById('aipet-fetch-models'), msg = document.getElementById('aipet-models-msg');
		btn.addEventListener('click', async () => {
			msg.textContent = '读取中…';
			try {
				const r = await fetch(<?php echo wp_json_encode( esc_url_raw( rest_url( 'ai-pet/v1/models' ) ) ); ?>, { headers: { 'X-WP-Nonce': <?php echo wp_json_encode( wp_create_nonce( 'wp_rest' ) ); ?> } });
				const d = await r.json();
				if (!r.ok) throw new Error(d.message || ('HTTP ' + r.status));
				const list = document.getElementById('aipet-models');
				list.replaceChildren(...d.models.map(id => Object.assign(document.createElement('option'), { value: id })));
				msg.textContent = '共 ' + d.models.length + ' 个，点输入框可以选择。';
			} catch (e) {
				msg.textContent = '读取失败：' + e.message;
			}
		});
	})();
	</script>
	<?php
}
