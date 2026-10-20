<?php
/**
 * REST 接口：
 * - POST ai-pet/v1/chat    访客聊天。只接受本站页面发来的请求，按 IP 和全站计数限流。发给模型的句子记进聊天记录（log.php）。
 * - GET  ai-pet/v1/models  后台「获取模型列表」，仅管理员。
 *
 * 出错时只返回错误代码（off / forbidden / bad / limit / error），由前端换成预设台词。
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_action( 'rest_api_init', 'aipet_register_routes' );

function aipet_register_routes() {
	register_rest_route(
		'ai-pet/v1',
		'/chat',
		array(
			'methods'             => 'POST',
			'callback'            => 'aipet_chat',
			'permission_callback' => '__return_true',
			'args'                => array(
				'message' => array( 'type' => 'string', 'required' => true ),
				'history' => array( 'type' => 'array', 'default' => array() ),
				'url'     => array( 'type' => 'string', 'default' => '' ),
				'sid'     => array( 'type' => 'string', 'default' => '' ),
			),
		)
	);
	register_rest_route(
		'ai-pet/v1',
		'/models',
		array(
			'methods'             => 'GET',
			'callback'            => 'aipet_models',
			'permission_callback' => function () {
				return current_user_can( 'manage_options' );
			},
		)
	);
}

function aipet_fail( $code, $status ) {
	return new WP_REST_Response( array( 'code' => $code ), $status );
}

/** 请求必须来自本站页面（Origin，没有时看 Referer）。 */
function aipet_same_site( WP_REST_Request $req ) {
	$from = $req->get_header( 'origin' ) ?: $req->get_header( 'referer' );
	return $from && wp_parse_url( $from, PHP_URL_HOST ) === wp_parse_url( home_url(), PHP_URL_HOST );
}

/**
 * 访客 IP。默认用 REMOTE_ADDR；站长在设置里选了 CDN / 反向代理时，改读对应的请求头
 * （X-Forwarded-For 取最后一个，也就是离本机最近的那层代理看到的地址）。读不到合法 IP 就退回 REMOTE_ADDR。
 */
function aipet_client_ip() {
	$remote = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
	$header = AIPET_IP_SOURCES[ aipet_opt( 'ip_source' ) ] ?? '';
	if ( '' !== $header && ! empty( $_SERVER[ $header ] ) ) {
		$list = array_map( 'trim', explode( ',', sanitize_text_field( wp_unslash( $_SERVER[ $header ] ) ) ) );
		$ip   = end( $list );
		if ( filter_var( $ip, FILTER_VALIDATE_IP ) ) {
			return $ip;
		}
	}
	return $remote;
}

/** 计一次数；超过任一限额就返回 false，且不计数。计数用的键里 IP 只存加盐哈希。 */
function aipet_take_quota() {
	$who  = substr( md5( aipet_client_ip() . wp_salt( 'nonce' ) ), 0, 12 );
	$keys = array(
		'aipet_h_' . $who . '_' . wp_date( 'YmdH' ) => array( (int) aipet_opt( 'per_hour' ), HOUR_IN_SECONDS ),
		'aipet_d_' . $who . '_' . wp_date( 'Ymd' )  => array( (int) aipet_opt( 'per_day' ), DAY_IN_SECONDS ),
		'aipet_s_' . wp_date( 'Ymd' )               => array( (int) aipet_opt( 'site_day' ), DAY_IN_SECONDS ),
	);
	$counts = array();
	foreach ( $keys as $key => list( $limit ) ) {
		$counts[ $key ] = (int) get_transient( $key );
		if ( $counts[ $key ] >= $limit ) {
			return false;
		}
	}
	foreach ( $keys as $key => list( , $ttl ) ) {
		set_transient( $key, $counts[ $key ] + 1, $ttl );
	}
	return true;
}

/** 前端传来的最近几轮对话：只保留 user / assistant 两种角色，去掉标签，限长。 */
function aipet_clean_history( $history ) {
	$out = array();
	foreach ( is_array( $history ) ? $history : array() as $m ) {
		if ( ! is_array( $m ) ) {
			continue;
		}
		$text = trim( wp_strip_all_tags( (string) ( $m['content'] ?? '' ) ) );
		if ( '' !== $text ) {
			$out[] = array(
				'role'    => 'assistant' === ( $m['role'] ?? '' ) ? 'assistant' : 'user',
				'content' => mb_substr( $text, 0, 400 ),
			);
		}
	}
	return array_slice( $out, -12 );
}

function aipet_chat( WP_REST_Request $req ) {
	if ( ! aipet_chat_ready() ) {
		return aipet_fail( 'off', 503 );
	}
	if ( ! aipet_same_site( $req ) ) {
		return aipet_fail( 'forbidden', 403 );
	}
	$message = trim( wp_strip_all_tags( (string) $req['message'] ) );
	if ( '' === $message || mb_strlen( $message ) > 200 ) {
		return aipet_fail( 'bad', 400 );
	}
	if ( ! aipet_take_quota() ) {
		return aipet_fail( 'limit', 429 );
	}

	$messages   = array( array( 'role' => 'system', 'content' => aipet_system_prompt( (string) $req['url'] ) ) );
	$messages   = array_merge( $messages, aipet_clean_history( $req['history'] ) );
	$messages[] = array( 'role' => 'user', 'content' => $message );

	$body = array(
		'model'       => aipet_opt( 'model' ),
		'messages'    => $messages,
		'max_tokens'  => 300,
		'temperature' => 0.8,
	);
	$res = aipet_post( $body );
	// 部分推理模型不接受 max_tokens / temperature，返回 400 时去掉它们再试一次。
	if ( ! is_wp_error( $res ) && 400 === wp_remote_retrieve_response_code( $res ) ) {
		unset( $body['max_tokens'], $body['temperature'] );
		$res = aipet_post( $body );
	}
	if ( is_wp_error( $res ) || 200 !== wp_remote_retrieve_response_code( $res ) ) {
		aipet_log( is_wp_error( $res ) ? $res->get_error_code() : 'HTTP ' . wp_remote_retrieve_response_code( $res ) );
		aipet_log_chat( $req, $message, '', 'error' );
		return aipet_fail( 'error', 502 );
	}

	$data  = json_decode( wp_remote_retrieve_body( $res ), true );
	$reply = (string) ( $data['choices'][0]['message']['content'] ?? '' );
	$reply = trim( preg_replace( '#<think>.*?</think>#su', '', $reply ) );
	if ( '' === $reply ) {
		aipet_log( 'empty reply' );
		aipet_log_chat( $req, $message, '', 'error' );
		return aipet_fail( 'error', 502 );
	}
	$reply = mb_substr( $reply, 0, 600 );
	aipet_log_chat( $req, $message, $reply, 'ok' );
	return array( 'reply' => $reply );
}

function aipet_post( $body ) {
	return wp_remote_post(
		aipet_opt( 'base_url' ) . '/chat/completions',
		array(
			'timeout' => 25,
			'headers' => array(
				'Authorization' => 'Bearer ' . get_option( AIPET_KEY_OPTION, '' ),
				'Content-Type'  => 'application/json',
			),
			'body'    => wp_json_encode( $body ),
		)
	);
}

/** 只在开着 WP_DEBUG_LOG 时记一行错误原因，不记 key、不记对话内容。 */
function aipet_log( $what ) {
	if ( defined( 'WP_DEBUG_LOG' ) && WP_DEBUG_LOG ) {
		error_log( '[ai-pet] chat failed: ' . $what ); // phpcs:ignore WordPress.PHP.DevelopmentFunctions
	}
}

function aipet_models() {
	$key = (string) get_option( AIPET_KEY_OPTION, '' );
	if ( '' === $key ) {
		return new WP_Error( 'aipet_no_key', '还没有保存 API key', array( 'status' => 400 ) );
	}
	if ( '' === aipet_opt( 'base_url' ) ) {
		return new WP_Error( 'aipet_no_url', '还没有保存接口地址', array( 'status' => 400 ) );
	}
	$res = wp_remote_get(
		aipet_opt( 'base_url' ) . '/models',
		array(
			'timeout' => 15,
			'headers' => array( 'Authorization' => 'Bearer ' . $key ),
		)
	);
	if ( is_wp_error( $res ) ) {
		return new WP_Error( 'aipet_models', '连接失败：' . $res->get_error_message(), array( 'status' => 502 ) );
	}
	$code = wp_remote_retrieve_response_code( $res );
	if ( 200 !== $code ) {
		return new WP_Error( 'aipet_models', '接口返回 HTTP ' . $code, array( 'status' => 502 ) );
	}
	$data = json_decode( wp_remote_retrieve_body( $res ), true );
	$ids  = array_values( array_filter( array_map( 'strval', wp_list_pluck( (array) ( $data['data'] ?? array() ), 'id' ) ) ) );
	sort( $ids );
	return array( 'models' => $ids );
}
