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
        <div className="p-6 text-center">
          <h2 className="text-2xl font-semibold">Verify Your Workspace Materialization Path</h2>
          <p className="mt-4 text-gray-700">
            Ensure your workspace is set up correctly and efficiently. Our tools help you streamline your workflow.
          </p>
        </div>
      </section>
      <section className="w-full p-6">
        <h2 className="text-xl font-semibold text-center">Our Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
          <div className="bg-white shadow-md rounded-lg overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-home-1/400/300"
              alt="Feature 1: Easy Setup"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="font-bold">Easy Setup</h3>
              <p className="text-gray-600">Quickly configure your workspace with our intuitive interface.</p>
            </div>
          </div>
          <div className="bg-white shadow-md rounded-lg overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-home-2/400/300"
              alt="Feature 2: Real-Time Collaboration"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="font-bold">Real-Time Collaboration</h3>
              <p className="text-gray-600">Work together with your team seamlessly, no matter where you are.</p>
            </div>
          </div>
          <div className="bg-white shadow-md rounded-lg overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-home-3/400/300"
              alt="Feature 3: Comprehensive Analytics"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="font-bold">Comprehensive Analytics</h3>
              <p className="text-gray-600">Gain insights into your workflow and optimize your processes.</p>
            </div>
          </div>
        </div>
      </section>
      <section className="w-full bg-blue-600 text-white py-6">
        <div className="text-center">
          <h2 className="text-2xl font-semibold">Get Started Today!</h2>
          <p className="mt-4">Join us and take your workspace to the next level.</p>
          <button className="mt-4 bg-white text-blue-600 font-bold py-2 px-4 rounded">
            Sign Up Now
          </button>
        </div>
      </section>
    </div>
  );
}
