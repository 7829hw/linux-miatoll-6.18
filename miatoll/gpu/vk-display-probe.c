// SPDX-License-Identifier: GPL-2.0-only
/*
 * Step-by-step Vulkan check for the curtana RAM test.
 *
 * vk-display-probe [seconds]
 *   1. Creates an instance with VK_KHR_display and prints the GPU.
 *   2. Runs vkCmdFillBuffer on a host-visible buffer and checks the result.
 *   3. Lists displays, modes and planes, creates a display plane surface and
 *      a swapchain, then presents frames cleared to red, green and blue in
 *      turn, one colour per second, for the given time (default 9 s).
 * Every step prints a line before it runs, so a crash shows where it stopped.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <vulkan/vulkan.h>

#define CHECK(call) do { VkResult r_ = (call); if (r_ != VK_SUCCESS) { \
	printf("VK_PROBE_FAIL %s = %d\n", #call, r_); return 1; } } while (0)
#define STEP(...) do { printf(__VA_ARGS__); printf("\n"); fflush(stdout); } while (0)

static VkInstance instance;
static VkPhysicalDevice gpu;
static VkDevice device;
static VkQueue queue;
static uint32_t queue_family;
static VkCommandPool pool;

static int memory_type(uint32_t bits, VkMemoryPropertyFlags flags, uint32_t *index)
{
	VkPhysicalDeviceMemoryProperties props;
	uint32_t i;

	vkGetPhysicalDeviceMemoryProperties(gpu, &props);
	for (i = 0; i < props.memoryTypeCount; i++)
		if ((bits & (1u << i)) && (props.memoryTypes[i].propertyFlags & flags) == flags) {
			*index = i;
			return 0;
		}
	return -1;
}

static int submit_and_wait(VkCommandBuffer cmd, VkSemaphore wait, VkSemaphore signal)
{
	VkPipelineStageFlags stage = VK_PIPELINE_STAGE_TRANSFER_BIT;
	VkSubmitInfo submit = {
		.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
		.waitSemaphoreCount = wait ? 1 : 0, .pWaitSemaphores = &wait, .pWaitDstStageMask = &stage,
		.commandBufferCount = 1, .pCommandBuffers = &cmd,
		.signalSemaphoreCount = signal ? 1 : 0, .pSignalSemaphores = &signal,
	};
	VkFenceCreateInfo fence_info = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
	VkFence fence;

	CHECK(vkCreateFence(device, &fence_info, NULL, &fence));
	CHECK(vkQueueSubmit(queue, 1, &submit, fence));
	CHECK(vkWaitForFences(device, 1, &fence, VK_TRUE, 5000000000ull));
	vkDestroyFence(device, fence, NULL);
	return 0;
}

static int fill_buffer_test(void)
{
	VkBufferCreateInfo info = {
		.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = 65536,
		.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT, .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
	};
	VkCommandBufferAllocateInfo alloc = {
		.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO, .commandPool = pool,
		.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1,
	};
	VkCommandBufferBeginInfo begin = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
	VkMemoryAllocateInfo mem_info = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
	VkMemoryRequirements req;
	VkCommandBuffer cmd;
	VkDeviceMemory memory;
	VkBuffer buffer;
	uint32_t *data, i, bad = 0;

	CHECK(vkCreateBuffer(device, &info, NULL, &buffer));
	vkGetBufferMemoryRequirements(device, buffer, &req);
	mem_info.allocationSize = req.size;
	if (memory_type(req.memoryTypeBits, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
			VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, &mem_info.memoryTypeIndex)) {
		printf("VK_PROBE_FAIL no host-visible memory\n");
		return 1;
	}
	CHECK(vkAllocateMemory(device, &mem_info, NULL, &memory));
	CHECK(vkBindBufferMemory(device, buffer, memory, 0));
	CHECK(vkMapMemory(device, memory, 0, VK_WHOLE_SIZE, 0, (void **)&data));
	memset(data, 0, info.size);
	CHECK(vkAllocateCommandBuffers(device, &alloc, &cmd));
	CHECK(vkBeginCommandBuffer(cmd, &begin));
	vkCmdFillBuffer(cmd, buffer, 0, VK_WHOLE_SIZE, 0x5a1a6180);
	CHECK(vkEndCommandBuffer(cmd));
	if (submit_and_wait(cmd, VK_NULL_HANDLE, VK_NULL_HANDLE))
		return 1;
	for (i = 0; i < info.size / 4; i++)
		bad += data[i] != 0x5a1a6180;
	printf("fill_buffer words=%u mismatches=%u\n", (unsigned)(info.size / 4), bad);
	vkUnmapMemory(device, memory);
	vkFreeCommandBuffers(device, pool, 1, &cmd);
	vkDestroyBuffer(device, buffer, NULL);
	vkFreeMemory(device, memory, NULL);
	return bad ? 1 : 0;
}

int main(int argc, char **argv)
{
	const char *instance_ext[] = { VK_KHR_SURFACE_EXTENSION_NAME, VK_KHR_DISPLAY_EXTENSION_NAME };
	const char *device_ext[] = { VK_KHR_SWAPCHAIN_EXTENSION_NAME };
	VkApplicationInfo app = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
				  .pApplicationName = "vk-display-probe", .apiVersion = VK_API_VERSION_1_1 };
	VkInstanceCreateInfo instance_info = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
		.pApplicationInfo = &app, .enabledExtensionCount = 2, .ppEnabledExtensionNames = instance_ext };
	float priority = 1.0f;
	VkDeviceQueueCreateInfo queue_info = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
		.queueCount = 1, .pQueuePriorities = &priority };
	VkDeviceCreateInfo device_info = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
		.queueCreateInfoCount = 1, .pQueueCreateInfos = &queue_info,
		.enabledExtensionCount = 1, .ppEnabledExtensionNames = device_ext };
	VkCommandPoolCreateInfo pool_info = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
		.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT };
	VkPhysicalDeviceProperties props;
	VkQueueFamilyProperties families[8];
	VkDisplayPropertiesKHR displays[4];
	VkDisplayModePropertiesKHR modes[16];
	VkDisplayPlanePropertiesKHR planes[8];
	VkDisplayKHR plane_displays[4];
	VkSurfaceCapabilitiesKHR caps;
	VkSurfaceFormatKHR formats[16];
	VkImage images[8];
	VkSurfaceKHR surface;
	VkSwapchainKHR swapchain;
	VkSemaphore acquired, rendered;
	VkCommandBuffer cmd;
	uint32_t count, i, j, plane = UINT32_MAX, frames = 0, seconds = argc > 1 ? atoi(argv[1]) : 9;
	struct timespec start, now;

	STEP("step instance");
	CHECK(vkCreateInstance(&instance_info, NULL, &instance));
	count = 1;
	vkEnumeratePhysicalDevices(instance, &count, &gpu);
	if (!count) {
		printf("VK_PROBE_FAIL no physical device\n");
		return 1;
	}
	vkGetPhysicalDeviceProperties(gpu, &props);
	printf("gpu %s api %u.%u.%u driver 0x%x\n", props.deviceName, VK_API_VERSION_MAJOR(props.apiVersion),
	       VK_API_VERSION_MINOR(props.apiVersion), VK_API_VERSION_PATCH(props.apiVersion), props.driverVersion);

	STEP("step device");
	count = 8;
	vkGetPhysicalDeviceQueueFamilyProperties(gpu, &count, families);
	for (queue_family = 0; queue_family < count; queue_family++)
		if (families[queue_family].queueFlags & VK_QUEUE_GRAPHICS_BIT)
			break;
	queue_info.queueFamilyIndex = queue_family;
	CHECK(vkCreateDevice(gpu, &device_info, NULL, &device));
	vkGetDeviceQueue(device, queue_family, 0, &queue);
	pool_info.queueFamilyIndex = queue_family;
	CHECK(vkCreateCommandPool(device, &pool_info, NULL, &pool));

	STEP("step fill_buffer");
	if (fill_buffer_test())
		return 1;
	STEP("VK_FILL_OK");

	STEP("step displays");
	count = 4;
	CHECK(vkGetPhysicalDeviceDisplayPropertiesKHR(gpu, &count, displays));
	for (i = 0; i < count; i++)
		printf("display %u name=%s %ux%u\n", i, displays[i].displayName ? displays[i].displayName : "(null)",
		       displays[i].physicalResolution.width, displays[i].physicalResolution.height);
	if (!count) {
		printf("VK_PROBE_FAIL no display\n");
		return 1;
	}
	count = 16;
	CHECK(vkGetDisplayModePropertiesKHR(gpu, displays[0].display, &count, modes));
	for (i = 0; i < count; i++)
		printf("mode %u %ux%u@%u\n", i, modes[i].parameters.visibleRegion.width,
		       modes[i].parameters.visibleRegion.height, modes[i].parameters.refreshRate);
	if (!count) {
		printf("VK_PROBE_FAIL no mode\n");
		return 1;
	}
	count = 8;
	CHECK(vkGetPhysicalDeviceDisplayPlanePropertiesKHR(gpu, &count, planes));
	for (i = 0; i < count && plane == UINT32_MAX; i++) {
		uint32_t n = 4;

		CHECK(vkGetDisplayPlaneSupportedDisplaysKHR(gpu, i, &n, plane_displays));
		for (j = 0; j < n; j++)
			if (plane_displays[j] == displays[0].display)
				plane = i;
	}
	printf("planes=%u chosen=%u\n", count, plane);
	if (plane == UINT32_MAX) {
		printf("VK_PROBE_FAIL no plane\n");
		return 1;
	}

	STEP("step surface");
	{
		VkDisplaySurfaceCreateInfoKHR info = {
			.sType = VK_STRUCTURE_TYPE_DISPLAY_SURFACE_CREATE_INFO_KHR,
			.displayMode = modes[0].displayMode, .planeIndex = plane,
			.transform = VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR, .alphaMode = VK_DISPLAY_PLANE_ALPHA_OPAQUE_BIT_KHR,
			.imageExtent = modes[0].parameters.visibleRegion,
		};
		VkBool32 supported = VK_FALSE;

		CHECK(vkCreateDisplayPlaneSurfaceKHR(instance, &info, NULL, &surface));
		CHECK(vkGetPhysicalDeviceSurfaceSupportKHR(gpu, queue_family, surface, &supported));
		CHECK(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(gpu, surface, &caps));
		count = 16;
		CHECK(vkGetPhysicalDeviceSurfaceFormatsKHR(gpu, surface, &count, formats));
		printf("surface supported=%u images=%u..%u extent=%ux%u usage=0x%x format0=%d formats=%u\n",
		       supported, caps.minImageCount, caps.maxImageCount, caps.currentExtent.width,
		       caps.currentExtent.height, caps.supportedUsageFlags, formats[0].format, count);
	}

	STEP("step swapchain");
	{
		VkSwapchainCreateInfoKHR info = {
			.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR, .surface = surface,
			.minImageCount = caps.minImageCount < 2 ? 2 : caps.minImageCount,
			.imageFormat = formats[0].format, .imageColorSpace = formats[0].colorSpace,
			.imageExtent = caps.currentExtent, .imageArrayLayers = 1,
			.imageUsage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
			.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE, .preTransform = caps.currentTransform,
			.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR, .presentMode = VK_PRESENT_MODE_FIFO_KHR,
			.clipped = VK_TRUE,
		};
		VkSemaphoreCreateInfo sem = { .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO };
		VkCommandBufferAllocateInfo alloc = {
			.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO, .commandPool = pool,
			.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1,
		};

		CHECK(vkCreateSwapchainKHR(device, &info, NULL, &swapchain));
		count = 8;
		CHECK(vkGetSwapchainImagesKHR(device, swapchain, &count, images));
		printf("swapchain images=%u\n", count);
		CHECK(vkCreateSemaphore(device, &sem, NULL, &acquired));
		CHECK(vkCreateSemaphore(device, &sem, NULL, &rendered));
		CHECK(vkAllocateCommandBuffers(device, &alloc, &cmd));
	}

	STEP("step present %us", seconds);
	clock_gettime(CLOCK_MONOTONIC, &start);
	for (;;) {
		static const VkClearColorValue colours[3] = {
			{ .float32 = { 1, 0, 0, 1 } }, { .float32 = { 0, 1, 0, 1 } }, { .float32 = { 0, 0, 1, 1 } } };
		VkImageSubresourceRange range = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 };
		VkCommandBufferBeginInfo begin = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
		VkImageMemoryBarrier barrier = { .sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
			.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED, .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
			.subresourceRange = range };
		VkPresentInfoKHR present = { .sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
			.waitSemaphoreCount = 1, .pWaitSemaphores = &rendered,
			.swapchainCount = 1, .pSwapchains = &swapchain };
		uint32_t index;
		double elapsed;

		clock_gettime(CLOCK_MONOTONIC, &now);
		elapsed = (now.tv_sec - start.tv_sec) + (now.tv_nsec - start.tv_nsec) / 1e9;
		if (elapsed >= seconds)
			break;
		CHECK(vkAcquireNextImageKHR(device, swapchain, 5000000000ull, acquired, VK_NULL_HANDLE, &index));
		CHECK(vkResetCommandBuffer(cmd, 0));
		CHECK(vkBeginCommandBuffer(cmd, &begin));
		barrier.image = images[index];
		barrier.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
		barrier.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
		barrier.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
		vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT,
				     0, 0, NULL, 0, NULL, 1, &barrier);
		vkCmdClearColorImage(cmd, images[index], VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
				     &colours[(int)elapsed % 3], 1, &range);
		barrier.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
		barrier.newLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
		barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
		barrier.dstAccessMask = 0;
		vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,
				     0, 0, NULL, 0, NULL, 1, &barrier);
		CHECK(vkEndCommandBuffer(cmd));
		if (submit_and_wait(cmd, acquired, rendered))
			return 1;
		present.pImageIndices = &index;
		CHECK(vkQueuePresentKHR(queue, &present));
		frames++;
	}
	printf("presented frames=%u in %us (%.1f fps)\n", frames, seconds, frames / (double)seconds);
	vkDeviceWaitIdle(device);
	vkDestroySwapchainKHR(device, swapchain, NULL);
	vkDestroySurfaceKHR(instance, surface, NULL);
	printf("VK_PROBE_OK\n");
	return 0;
}
