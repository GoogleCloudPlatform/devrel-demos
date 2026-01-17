package godoc

import (
	"context"
	"testing"

	"golang.org/x/tools/go/packages"
)

func BenchmarkLoad(b *testing.B) {
	ctx := context.Background()
	pkgPath := "os/exec"
	symbol := "Cmd"

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := Load(ctx, pkgPath, symbol)
		if err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkExtract(b *testing.B) {
	ctx := context.Background()
	pkgPath := "os/exec"
	symbol := "Cmd"

	// Pre-load to simulate file_read state
	cfg := &packages.Config{
		Context: ctx,
		Mode:    packages.NeedTypes | packages.NeedSyntax | packages.NeedTypesInfo | packages.NeedName | packages.NeedImports | packages.NeedFiles | packages.NeedDeps,
	}
	pkgs, err := packages.Load(cfg, pkgPath)
	if err != nil || len(pkgs) == 0 {
		b.Fatalf("failed to load package: %v", err)
	}
	pkg := pkgs[0]

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := Extract(pkg, symbol)
		if err != nil {
			b.Fatal(err)
		}
	}
}
