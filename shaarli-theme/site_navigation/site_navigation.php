<?php

/**
 * Add the main website navigation and an All link to Shaarli's toolbar.
 */
function hook_site_navigation_render_header($data)
{
    $globalLinks = require __DIR__ . '/navigation.generated.php';

    foreach ($globalLinks as $link) {
        ['slug' => $slug, 'href' => $href, 'label' => $label] = $link;
        $class = 'site-navigation-link site-navigation-' . $slug;
        $attributes = [
            'href' => $href,
            'class' => $class,
        ];
        if ($slug === 'links') {
            $attributes['aria-current'] = 'page';
        }
        $data['buttons_toolbar'][] = [
            'class' => $class,
            'attr' => $attributes,
            'html' => $label,
        ];
    }

    $localClass = 'site-navigation-local site-navigation-all';
    $data['buttons_toolbar'][] = [
        'class' => $localClass,
        'attr' => [
            'href' => $data['_BASE_PATH_'] . '/',
            'class' => $localClass,
        ],
        'html' => 'All',
    ];

    return $data;
}
