export default function Home() {
  return (
    <div className="flex flex-col items-center bg-gray-100">
      <header className="w-full bg-blue-600 text-white py-6">
        <h1 className="text-3xl font-bold text-center">WorkspaceDirTest</h1>
      </header>
      <section className="w-full">
        <img
          src="https://picsum.photos/seed/hero-home/1200/700"
          alt="A modern workspace setup"
          className="w-full h-auto"
        />
        <div className="p-6">
          <h2 className="text-2xl font-semibold text-center">Verify Your Workspace</h2>
          <p className="mt-4 text-center text-gray-700">
            Ensure your workspace materialization path is optimized for productivity and efficiency.
          </p>
        </div>
      </section>
      <section className="w-full py-8 bg-white">
        <h2 className="text-2xl font-semibold text-center">Our Services</h2>
        <div className="flex justify-around mt-6">
          <div className="max-w-xs bg-gray-200 rounded-lg shadow-md p-4">
            <img
              src="https://picsum.photos/seed/card-home-1/300/200"
              alt="Service 1"
              className="w-full h-auto rounded-t-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Workspace Optimization</h3>
            <p className="text-gray-600">Enhance your workspace layout for better efficiency.</p>
          </div>
          <div className="max-w-xs bg-gray-200 rounded-lg shadow-md p-4">
            <img
              src="https://picsum.photos/seed/card-home-2/300/200"
              alt="Service 2"
              className="w-full h-auto rounded-t-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Materialization Path Analysis</h3>
            <p className="text-gray-600">Analyze and improve your materialization strategies.</p>
          </div>
          <div className="max-w-xs bg-gray-200 rounded-lg shadow-md p-4">
            <img
              src="https://picsum.photos/seed/card-home-3/300/200"
              alt="Service 3"
              className="w-full h-auto rounded-t-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Consultation Services</h3>
            <p className="text-gray-600">Get expert advice tailored to your workspace needs.</p>
          </div>
        </div>
      </section>
      <section className="w-full py-8 bg-blue-100">
        <h2 className="text-2xl font-semibold text-center">Get Started Today!</h2>
        <p className="mt-4 text-center text-gray-700">
          Contact us to begin your journey towards an optimized workspace.
        </p>
        <div className="flex justify-center mt-6">
          <a
            href="#"
            className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
          >
            Contact Us
          </a>
        </div>
      </section>
    </div>
  );
}
