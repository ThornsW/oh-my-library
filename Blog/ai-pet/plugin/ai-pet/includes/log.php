<?php
/**
 * 聊天记录：访客的每句话和角色的回答存进自建表 {prefix}aipet_log，保留天数在设置里（默认 30），
 * 每天由 WP-Cron 删掉过期的。后台「AI 宠物 → 聊天记录」按对话分组查看。
 *
 * 只记通过了来源检查和限流、真正发给模型的句子；被拒绝的请求不记，免得有人刷接口把表撑大。
 * 一段对话 = 同一个浏览器标签页（前端在 sessionStorage 里生成的 sid）+ 同一个 IP。
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

const AIPET_DB_VERSION = 1;

function aipet_log_table() {
	global $wpdb;
	return $wpdb->prefix . 'aipet_log';
}

add_action( 'plugins_loaded', 'aipet_maybe_install' );

/** 表结构版本和 option 里记的不一致时建表或升级。直接覆盖插件文件更新时也会走到这里。 */
function aipet_maybe_install() {
	if ( AIPET_DB_VERSION === (int) get_option( 'aipet_db_version' ) ) {
		return;
	}
	global $wpdb;
	require_once ABSPATH . 'wp-admin/includes/upgrade.php';
	$table   = aipet_log_table();
	$collate = $wpdb->get_charset_collate();
	dbDelta(
		"CREATE TABLE $table (
  id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  created_at datetime NOT NULL,
  ip varchar(45) NOT NULL DEFAULT '',
  sid varchar(36) NOT NULL DEFAULT '',
  page varchar(500) NOT NULL DEFAULT '',
  model varchar(100) NOT NULL DEFAULT '',
  message text NOT NULL,
  reply text NOT NULL,
  status varchar(10) NOT NULL DEFAULT 'ok',
  PRIMARY KEY  (id),
  KEY created_at (created_at),
  KEY sid (sid)
) $collate;"
	);
	update_option( 'aipet_db_version', AIPET_DB_VERSION );
}

add_action( 'init', 'aipet_schedule_cleanup' );
add_action( 'aipet_log_cleanup', 'aipet_log_cleanup' );

function aipet_schedule_cleanup() {
	if ( ! wp_next_scheduled( 'aipet_log_cleanup' ) ) {
		wp_schedule_event( time() + HOUR_IN_SECONDS, 'daily', 'aipet_log_cleanup' );
	}
}

function aipet_log_cleanup() {
	global $wpdb;
	$wpdb->query( $wpdb->prepare( 'DELETE FROM ' . aipet_log_table() . ' WHERE created_at < %s', gmdate( 'Y-m-d H:i:s', time() - (int) aipet_opt( 'log_days' ) * DAY_IN_SECONDS ) ) ); // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared
}

/** 记一句。$status：ok 正常回答；error 接口出错（前端改说预设台词）。 */
function aipet_log_chat( WP_REST_Request $req, $message, $reply, $status ) {
	if ( ! aipet_opt( 'log_enabled' ) ) {
		return;
	}
	global $wpdb;
	$sid  = (string) $req['sid'];
	$page = (string) $req['url'];
	$wpdb->insert(
		aipet_log_table(),
		array(
			'created_at' => current_time( 'mysql', true ),
			'ip'         => aipet_log_visitor(),
			'sid'        => preg_match( '/^[A-Za-z0-9-]{8,36}$/', $sid ) ? $sid : '',
			'page'       => wp_parse_url( $page, PHP_URL_HOST ) === wp_parse_url( home_url(), PHP_URL_HOST ) ? mb_substr( esc_url_raw( $page ), 0, 500 ) : '',
			'model'      => mb_substr( (string) aipet_opt( 'model' ), 0, 100 ),
			'message'    => $message,
			'reply'      => $reply,
			'status'     => $status,
		)
	);
}

/** 记进表里的访客标识：IP 原文，或者（设置里关掉记录 IP 时）由 IP 加盐哈希出的匿名编号。 */
function aipet_log_visitor() {
	$ip = aipet_client_ip();
	return aipet_opt( 'log_ip' ) ? $ip : '匿名-' . substr( hash_hmac( 'sha256', $ip, wp_salt( 'nonce' ) ), 0, 8 );
}

// ---------- 后台「聊天记录」页 ----------

/** 页面网址 → 「《标题》」或路径，同一次请求里缓存。 */
function aipet_log_page_label( $url ) {
	static $seen = array();
	if ( '' === $url ) {
		return '';
	}
	if ( ! isset( $seen[ $url ] ) ) {
		$id = url_to_postid( $url );
		if ( $id ) {
			$seen[ $url ] = '《' . get_the_title( $id ) . '》';
		} else {
			$path         = (string) wp_parse_url( $url, PHP_URL_PATH );
			$query        = (string) wp_parse_url( $url, PHP_URL_QUERY );
			$label        = rawurldecode( $path . ( '' !== $query ? '?' . $query : '' ) );
			$seen[ $url ] = in_array( $label, array( '', '/' ), true ) ? '首页' : $label;
		}
	}
	return $seen[ $url ];
}

function aipet_log_page() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	global $wpdb;
	$table = aipet_log_table();
	// 只读的筛选参数，不改数据，所以不需要 nonce。
	$ip    = isset( $_GET['ip'] ) ? sanitize_text_field( wp_unslash( $_GET['ip'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification
	$q     = isset( $_GET['q'] ) ? trim( sanitize_text_field( wp_unslash( $_GET['q'] ) ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification
	$paged = max( 1, isset( $_GET['paged'] ) ? (int) $_GET['paged'] : 1 ); // phpcs:ignore WordPress.Security.NonceVerification
	$per   = 20;

	$where = array( '1=1' );
	$args  = array();
	if ( '' !== $ip ) {
		$where[] = 'ip = %s';
		$args[]  = $ip;
	}
	if ( '' !== $q ) {
		$where[] = '(message LIKE %s OR reply LIKE %s)';
		$like    = '%' . $wpdb->esc_like( $q ) . '%';
		$args[]  = $like;
		$args[]  = $like;
	}
	$where = implode( ' AND ', $where );
	$prep  = fn( $sql, $extra = array() ) => $args || $extra ? $wpdb->prepare( $sql, ...array_merge( $args, $extra ) ) : $sql; // phpcs:ignore WordPress.DB.PreparedSQL

	// 先按对话分组（sid + ip）分页，再取每段对话的全部句子；搜索时显示命中的整段对话。
	$total  = (int) $wpdb->get_var( $prep( "SELECT COUNT(*) FROM (SELECT 1 FROM $table WHERE $where GROUP BY sid, ip) g" ) );
	$groups = $wpdb->get_results( $prep( "SELECT sid, ip, MAX(created_at) AS last_at FROM $table WHERE $where GROUP BY sid, ip ORDER BY last_at DESC LIMIT %d OFFSET %d", array( $per, ( $paged - 1 ) * $per ) ) );

	$since = gmdate( 'Y-m-d H:i:s', time() - (int) aipet_opt( 'log_days' ) * DAY_IN_SECONDS );
	$stats = $wpdb->get_row( $wpdb->prepare( "SELECT COUNT(*) AS n, COUNT(DISTINCT ip) AS ips, COUNT(DISTINCT sid, ip) AS convs FROM $table WHERE created_at >= %s", $since ) ); // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
	$base  = admin_url( 'admin.php?page=ai-pet' );
	$pet   = (string) aipet_opt( 'pet_name' );
	?>
	<div class="wrap aipet-log">
		<h1>聊天记录</h1>
		<p>最近 <?php echo esc_html( aipet_opt( 'log_days' ) ); ?> 天：<strong><?php echo esc_html( $stats->convs ); ?></strong> 段对话，
			<strong><?php echo esc_html( $stats->n ); ?></strong> 句，来自 <strong><?php echo esc_html( $stats->ips ); ?></strong> 个 IP。
			今天全站已聊 <strong><?php echo esc_html( (int) get_transient( 'aipet_s_' . wp_date( 'Ymd' ) ) ); ?></strong> 句（上限 <?php echo esc_html( aipet_opt( 'site_day' ) ); ?>）。
			记录保留 <?php echo esc_html( aipet_opt( 'log_days' ) ); ?> 天，过期自动删除。被限额或来源检查挡下的请求不记录。</p>

		<form method="get" class="aipet-log-filter">
			<input type="hidden" name="page" value="ai-pet">
			<?php if ( '' !== $ip ) : ?>
				<input type="hidden" name="ip" value="<?php echo esc_attr( $ip ); ?>">
			<?php endif; ?>
			<input type="search" name="q" value="<?php echo esc_attr( $q ); ?>" placeholder="搜索访客或角色说的话">
			<button class="button">搜索</button>
			<?php if ( '' !== $ip || '' !== $q ) : ?>
				<span class="aipet-log-on">
					<?php echo '' !== $ip ? '只看 IP ' . esc_html( $ip ) : ''; ?>
					<?php echo '' !== $q ? ' 含「' . esc_html( $q ) . '」' : ''; ?>
					· 共 <?php echo esc_html( $total ); ?> 段 · <a href="<?php echo esc_url( $base ); ?>">显示全部</a>
				</span>
			<?php endif; ?>
		</form>

		<?php if ( ! $groups ) : ?>
			<p class="aipet-log-empty">还没有聊天记录。</p>
		<?php endif; ?>
		<?php if ( ! aipet_opt( 'log_enabled' ) ) : ?>
			<div class="notice notice-warning inline"><p>聊天记录已在「设置」里关闭，新的对话不会被记录。</p></div>
		<?php endif; ?>

		<?php
		foreach ( $groups as $g ) :
			$rows = $wpdb->get_results( $wpdb->prepare( "SELECT * FROM $table WHERE sid = %s AND ip = %s ORDER BY id", $g->sid, $g->ip ) ); // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
			if ( ! $rows ) {
				continue;
			}
			$first = $rows[0]->created_at;
			$last  = end( $rows )->created_at;
			?>
			<div class="aipet-conv">
				<div class="aipet-conv-head">
					<strong><?php echo esc_html( get_date_from_gmt( $first, 'm-d H:i' ) ); ?></strong>
					<?php if ( get_date_from_gmt( $first, 'm-d H:i' ) !== get_date_from_gmt( $last, 'm-d H:i' ) ) : ?>
						– <?php echo esc_html( get_date_from_gmt( $last, substr( $first, 0, 10 ) === substr( $last, 0, 10 ) ? 'H:i' : 'm-d H:i' ) ); ?>
					<?php endif; ?>
					· <a href="<?php echo esc_url( add_query_arg( 'ip', rawurlencode( $g->ip ), $base ) ); ?>" title="只看这个 IP"><?php echo esc_html( $g->ip ); ?></a>
					· <?php echo esc_html( count( $rows ) ); ?> 句
				</div>
				<?php foreach ( $rows as $r ) : ?>
					<div class="aipet-turn">
						<div class="aipet-meta">
							<?php echo esc_html( get_date_from_gmt( $r->created_at, 'H:i:s' ) ); ?>
							<?php if ( '' !== $r->page ) : ?>
								· 在 <a href="<?php echo esc_url( $r->page ); ?>" target="_blank" rel="noopener"><?php echo esc_html( aipet_log_page_label( $r->page ) ); ?></a>
							<?php endif; ?>
							<?php if ( '' !== $r->model ) : ?>
								· <?php echo esc_html( $r->model ); ?>
							<?php endif; ?>
						</div>
						<div class="aipet-q"><b>访客</b><span><?php echo esc_html( $r->message ); ?></span></div>
						<?php if ( 'ok' === $r->status ) : ?>
							<div class="aipet-a"><b><?php echo esc_html( $pet ); ?></b><span><?php echo esc_html( $r->reply ); ?></span></div>
						<?php else : ?>
							<div class="aipet-a is-error"><b><?php echo esc_html( $pet ); ?></b><span>（接口出错，改说了预设台词）</span></div>
						<?php endif; ?>
					</div>
				<?php endforeach; ?>
			</div>
		<?php endforeach; ?>

		<?php
		$links = paginate_links(
			array(
				'base'      => add_query_arg( 'paged', '%#%' ),
				'format'    => '',
				'current'   => $paged,
				'total'     => (int) ceil( $total / $per ),
				'prev_text' => '‹ 较新',
				'next_text' => '较早 ›',
			)
		);
		if ( $links ) {
			echo '<div class="tablenav"><div class="tablenav-pages">' . wp_kses_post( $links ) . '</div></div>';
		}
		?>
	</div>
	<style>
		.aipet-log-filter { margin: 12px 0 16px; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
		.aipet-log-filter input[type=search] { width: 260px; max-width: 100%; }
		.aipet-log-on { color: #50575e; }
		.aipet-conv { background: #fff; border: 1px solid #dcdcde; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; max-width: 900px; }
		.aipet-conv-head { color: #50575e; padding-bottom: 8px; border-bottom: 1px solid #f0f0f1; margin-bottom: 4px; }
		.aipet-turn { padding: 8px 0; border-bottom: 1px dashed #f0f0f1; }
		.aipet-turn:last-child { border-bottom: 0; }
		.aipet-meta { color: #8c8f94; font-size: 12px; margin-bottom: 4px; }
		.aipet-q, .aipet-a { display: flex; gap: 10px; line-height: 1.6; }
		.aipet-q b, .aipet-a b { flex: none; min-width: 3em; max-width: 8em; color: #50575e; }
		.aipet-q span, .aipet-a span { white-space: pre-wrap; word-break: break-word; }
		.aipet-a b { color: <?php echo esc_html( aipet_opt( 'color_light' ) ); ?>; }
		.aipet-a.is-error span { color: #b32d2e; }
	</style>
	<?php
}
