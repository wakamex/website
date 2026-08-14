<?php

use Shaarli\Config\ConfigJson;

if ($argc !== 2) {
    fwrite(STDERR, "Usage: configure_links.php SHAARLI_ROOT\n");
    exit(2);
}

$root = rtrim($argv[1], '/');
require $root . '/vendor/autoload.php';

$path = $root . '/data/config.json.php';
$io = new ConfigJson();
$config = $io->read($path);

$config['general']['title'] = 'Links';
$config['general']['header_link'] = '/links/';

$plugins = $config['general']['enabled_plugins'] ?? [];
if (!in_array('site_navigation', $plugins, true)) {
    $plugins[] = 'site_navigation';
}
$config['general']['enabled_plugins'] = array_values($plugins);

$io->write($path . '.new', $config);
