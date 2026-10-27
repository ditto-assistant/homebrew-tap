class Heyditto < Formula
  desc "Ditto memory, inference, and code review from the terminal"
  homepage "https://github.com/ditto-assistant/ditto-cli"
  url "https://registry.npmjs.org/@heyditto/cli/-/cli-2.33.0.tgz"
  sha256 "69bbd98157d9b730be5ad8bdb0a60aedcb31d31ac74c8e5d42836038b1727376"
  license "MIT"

  depends_on "node@24"

  resource "dependency-lock" do
    url "https://raw.githubusercontent.com/ditto-assistant/ditto-cli/2d1f3c726a63a2e16bb1ab94b133544252c70eaa/package-lock.json"
    sha256 "27ed3c0f9540b5e839e70f8a4cb20b5018babed0da34083008d38545d47ca906"
  end

  def install
    node = Formula["node@24"]
    odie "Node 24.22.1 or newer in the 24.x line is required" if node.version < Version.new("24.22.1")
    ENV.prepend_path "PATH", node.opt_bin
    resource("dependency-lock").stage { buildpath.install "package-lock.json" }
    # npm ci verifies the locked dependency integrity; never run lifecycle scripts.
    system node.opt_bin/"npm", "ci", "--omit=dev", "--ignore-scripts", "--no-audit", "--no-fund"
    libexec.install Dir["*"]
    (libexec/"INSTALL_METHOD").write "homebrew\n"
    (bin/"heyditto").write <<~EOS
      #!/bin/sh
      export HEYDITTO_INSTALL_METHOD=homebrew
      export HEYDITTO_NO_UPDATE=1
      exec "#{node.opt_bin}/node" "#{libexec}/dist/cli.js" "$@"
    EOS
  end

  test do
    assert_equal "homebrew\n", (libexec/"INSTALL_METHOD").read
    assert_match version.to_s, shell_output("#{bin}/heyditto --version")
    assert_match "review", shell_output("#{bin}/heyditto --help")
    system "git", "init", "--quiet"
    system "git", "config", "user.email", "brew-test@example.invalid"
    system "git", "config", "user.name", "Homebrew test"
    (testpath/"sample.txt").write "before\n"
    system "git", "add", "sample.txt"
    system "git", "commit", "--quiet", "-m", "fixture"
    (testpath/"sample.txt").atomic_write "after\n"
    # Fail closed if a future preview tries to use an account or network.
    (testpath/"deny-network.cjs").write <<~JS
      const deny = () => { throw new Error("network forbidden in offline preview"); };
      globalThis.fetch = deny;
      for (const name of ["http", "https", "net", "tls"]) {
        const mod = require(name);
        for (const method of ["request", "get", "connect", "createConnection"]) {
          if (mod[method]) mod[method] = deny;
        }
      }
    JS
    ENV.delete "DITTO_API_KEY"
    ENV["HOME"] = testpath.to_s
    ENV["XDG_CONFIG_HOME"] = (testpath/"config").to_s
    ENV["NODE_OPTIONS"] = "--require=#{testpath}/deny-network.cjs"
    output = shell_output("#{bin}/heyditto review local --preview --output json")
    preview = JSON.parse(output)
    assert_includes preview.fetch("changedPaths"), "sample.txt"
    assert_match(/\A[0-9a-f]{64}\z/, preview.fetch("snapshotDigest"))
  end
end
