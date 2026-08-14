<?php

declare(strict_types=1);

namespace Acme\Adaptive\Tests\Unit;

use Acme\Adaptive\Service\GreetingService;
use PHPUnit\Framework\TestCase;

final class GreetingServiceTest extends TestCase
{
    public function testGreetsNamedUser(): void
    {
        self::assertSame('Hello, Dmitry', (new GreetingService())->greet(' Dmitry '));
    }

    public function testFallsBackForBlankName(): void
    {
        self::assertSame('Hello', (new GreetingService())->greet('   '));
    }
}
