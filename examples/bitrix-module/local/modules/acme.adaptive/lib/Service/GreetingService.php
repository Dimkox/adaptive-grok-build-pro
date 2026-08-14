<?php

declare(strict_types=1);

namespace Acme\Adaptive\Service;

final class GreetingService
{
    public function greet(string $name): string
    {
        $name = trim($name);
        return $name === '' ? 'Hello' : sprintf('Hello, %s', $name);
    }
}
